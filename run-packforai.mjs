#!/usr/bin/env node
// PackForAI side of the "PackForAI vs Microsoft MarkItDown" document-to-Markdown benchmark.
//
//   node run-packforai.mjs <inputDir> <outDir>
//
// Build the worker first:  cd aireadydoc/services/worker && npm run build
//
// Every regular, non-hidden file directly inside <inputDir> is an input. The listing is not recursive, so
// sub-folders such as ground-truth/ are skipped. For each input the runner builds the job record that
// production builds for a free-plan upload without OCR, passes it with the file's bytes to processInput()
// from the compiled worker (../../services/worker/dist/processor.js) and writes
//   <outDir>/<file>.packforai.document.md   files.markdown        (document.md of a production package)
//   <outDir>/<file>.packforai.compact.md    files.compactMarkdown (compact.md of a production package)
//   <outDir>/<file>.packforai.json          ok/error, tokenAnalysis, textQuality, processingNotes, elapsedMs,
//                                           workerGitCommit, nodeVersion, the job record and run details
// A file that fails is recorded in its .json with ok: false and the run goes on. Its .md files are not
// written, and copies left by an earlier run are deleted. Results in <outDir> for names that are not inputs of
// this run are kept and listed in a warning. The exit code is 0 once every file has a result, 2 for a usage
// or setup error.
//
// tokenAnalysis is the worker's own figure: originalTokenEstimate counts the extracted plain text
// (extracted.rawText), not document.md; optimizedTokenEstimate counts compact.md. Both turn CRLF into LF first
// and fall back to characters / 4 (tokenizerName says so) above 1.5 million characters or when the text holds a
// special-token string such as "<|endoftext|>". outputs.*.tokensO200k counts each written file as stored, like
// score.mjs: gpt-tokenizer o200k_base, special-token strings counted as ordinary text, no size cap.
//
// Isolation. Conversions run in a child process that cannot reach the network, Firestore or Cloud Storage.
// Before the worker is imported, the child replaces globalThis.fetch with a function that throws and makes
// socket connects, DNS lookups, child processes, worker threads and UDP sockets throw as well, because
// google-auth-library sends its token and metadata requests through node-fetch and Firestore uses gRPC, and
// neither goes through globalThis.fetch. Cloud settings are removed from the child's environment and
// GOOGLE_APPLICATION_CREDENTIALS points at a file that does not exist. Importing processor.js still runs
// firebase.ts (initializeApp() and getFirestore()) and constructs two GoogleAuth objects. In firebase-admin
// 14.1.0, @google-cloud/firestore 8.6.0 and google-auth-library 10.9.0 these only store options until a
// method is called: they load no credentials and open no connection, and processInput() with
// ocrRequested: false calls none of them. A blocked attempt during a conversion fails that file.
//
// Where production decides the job fields (paths relative to aireadydoc/):
//   fileType  the text after the last "." of the uploaded file name, lower-cased, if it is one of
//             SUPPORTED_FILE_TYPES. The content is never sniffed. Web upload: getSupportedType(file.name) in
//             apps/web/src/app/home-client.tsx, checked again by apps/web/src/app/api/jobs/route.ts. Public
//             API: detectFileType(fileName) in apps/web/src/app/api/v1/convert/route.ts and v1/batch/route.ts.
//   fileName  the uploaded name, trimmed (parseCreateJobBody in api/jobs/route.ts; the API uses
//             file.name?.trim() || "document"). It becomes the title and the "Source" line of both outputs.
//   job       createQueuedJob() in apps/web/src/lib/server/job-pipeline.ts for a free-plan user
//             (planLimits.free in apps/web/src/lib/plans.ts) with ocrRequested: false. The web form offers
//             OCR only on Pro, Scale and Day Pass, and only for PDFs.
//   claim     claimQueuedJob() in services/worker/src/jobs.ts: status "processing", attemptCount + 1,
//             ocrReservedPages 0. processJob() in services/worker/src/processor.ts then downloads the
//             upload and calls processInput(job, bytes).
// Only fileType, fileName and ocrRequested change document.md and compact.md. The plan, ids, sizes and OCR
// limits reach only processing-report.md, README_FOR_AI.md, manifest.json or Firestore.

import { execFileSync, fork } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import { mkdir, readFile, readdir, rename, rm, stat, writeFile } from "node:fs/promises";
import { createRequire, syncBuiltinESMExports } from "node:module";
import os from "node:os";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath, pathToFileURL } from "node:url";
import { format } from "node:util";

const SCHEMA = "packforai-benchmark-result@1";

const RUNNER_FILE = fileURLToPath(import.meta.url);
const BENCH_DIR = path.dirname(RUNNER_FILE);
const REPO_ROOT = path.resolve(BENCH_DIR, "../../..");
const WORKER_DIR = path.resolve(BENCH_DIR, "../../services/worker");
const DIST_DIR = path.join(WORKER_DIR, "dist");
const PROCESSOR_URL = new URL("../../services/worker/dist/processor.js", import.meta.url);
const PROCESSOR_FILE = fileURLToPath(PROCESSOR_URL);

const SUPPORTED_FILE_TYPES = ["pdf", "docx", "pptx", "xlsx", "csv", "json"];
// planLimits.free in apps/web/src/lib/plans.ts
const FREE_PLAN = {
  plan: "free",
  dailyConversionLimit: 3,
  maxActiveJobs: 1,
  maxFileSizeBytes: 10 * 1024 * 1024,
  monthlyOcrPageLimit: 0,
  maxOcrPagesPerJob: 0
};
const PRODUCT_MAX_FILE_BYTES = 50 * 1024 * 1024; // maxSupportedFileSize in job-pipeline.ts (largest plan limit)
const WEB_MAX_FILE_NAME_LENGTH = 240; // parseCreateJobBody in api/jobs/route.ts
const PROCESSING_VERSION = "mvp-0.1.0"; // createQueuedJob in job-pipeline.ts
const BENCH_USER_ID = "benchmark-local";
const PRODUCTION_RUNTIME = "node:22-slim with NODE_ENV=production (aireadydoc/services/worker/Dockerfile)";
const TIMING_NOTE =
  "elapsedMs is the wall time of processInput(job, bytes) in a long-lived conversion process that first " +
  "converted one small generated file of each type. It excludes reading the file, the Storage download " +
  "and upload, Firestore updates and queueing.";

// services/worker/src/ocr.ts refers to the worker's 300 s request timeout.
const FILE_TIMEOUT_MS = readPositiveInt("PACKFORAI_BENCH_FILE_TIMEOUT_MS", 300_000);
const STARTUP_TIMEOUT_MS = 120_000;
const MAX_CONSOLE_LINES = 50;

// Files that decide how dist/ is compiled and how production builds the job (relative to the worker folder).
const WATCHED_SOURCE_PATHS = [
  "src",
  "package.json",
  "tsconfig.json",
  "../../../tsconfig.base.json",
  "../../../package-lock.json",
  "../../apps/web/src/lib/server/job-pipeline.ts",
  "../../apps/web/src/lib/plans.ts",
  "../../apps/web/src/app/home-client.tsx",
  "../../apps/web/src/app/api/jobs/route.ts",
  "../../apps/web/src/app/api/v1/convert/route.ts",
  "../../apps/web/src/app/api/v1/batch/route.ts"
];
// Packages whose code produces or counts the outputs, plus the cloud clients that are constructed on import.
const RECORDED_PACKAGES = [
  "pdf-parse",
  "mammoth",
  "turndown",
  "@mixmark-io/domino",
  "fast-xml-parser",
  "fflate",
  "gpt-tokenizer",
  "firebase-admin",
  "@google-cloud/firestore",
  "google-auth-library"
];

const USAGE = `Usage: node run-packforai.mjs <inputDir> <outDir>

Converts every non-hidden file directly inside <inputDir> with the compiled PackForAI worker, as a free-plan
job without OCR, and writes <file>.packforai.document.md, <file>.packforai.compact.md and
<file>.packforai.json to <outDir>. Sub-folders (such as ground-truth/) are skipped.
Build the worker first: cd aireadydoc/services/worker && npm run build
`;

// ---------------------------------------------------------------------------------------------------------
// Production rules, shared by the parent and the conversion process (exported for other benchmark scripts).

/** What production accepts for an uploaded file, decided from its name and size as the upload routes do. */
export function classifyUpload(name, size) {
  const fileName = name.trim() || "document";
  // Exactly detectFileType() in api/v1/convert/route.ts: the text after the last "." (the whole name when
  // there is none), lower-cased. getSupportedType() in home-client.tsx does the same on the untrimmed name.
  const extension = fileName.split(".").pop().toLowerCase();
  const fileType = SUPPORTED_FILE_TYPES.includes(extension) ? extension : null;
  const rejection = !fileType
    ? {
        code: "UNSUPPORTED_FILE_TYPE",
        message: `${fileName.includes(".") ? `".${extension}"` : "A file name without an extension"} is not accepted: production takes only .pdf, .docx, .pptx, .xlsx, .csv and .json uploads and decides by the extension.`
      }
    : size <= 0
      ? { code: "EMPTY_FILE", message: "Production rejects empty uploads." }
      : size > PRODUCT_MAX_FILE_BYTES
        ? { code: "FILE_TOO_LARGE", message: "File exceeds the 50.0 MB product limit (the largest plan limit)." }
        : null;
  const notes = [];
  if (fileName !== name) notes.push(`Production trims the file name, so the job uses "${fileName}".`);
  if (!rejection && size > FREE_PLAN.maxFileSizeBytes) {
    notes.push("Larger than the 10 MB free-plan upload limit: production rejects it on the free plan, while Pro, Scale and Day Pass accept up to 50 MB. The conversion does not depend on the plan.");
  }
  if (fileName.length > WEB_MAX_FILE_NAME_LENGTH) {
    notes.push("The web upload rejects file names longer than 240 characters; the public API accepts them.");
  }
  return {
    fileName,
    fileType,
    rejectedByProduction: Boolean(rejection),
    rejection,
    freePlanUpload: !rejection && size <= FREE_PLAN.maxFileSizeBytes,
    notes
  };
}

/** The job record processInput() receives in production for a free-plan upload without OCR. */
export function buildProductionJob({ fileName, fileType, fileSize, sha256: contentHash, now = new Date() }) {
  const jobId = `bench_${contentHash.slice(0, 32)}`;
  // createQueuedJob() in apps/web/src/lib/server/job-pipeline.ts writes this document to jobs/{jobId}.
  const queued = {
    jobId,
    userId: BENCH_USER_ID,
    documentId: jobId,
    fileName,
    fileType,
    fileSize,
    uploadPath: `uploads/${BENCH_USER_ID}/${jobId}/original.${fileType}`,
    status: "queued",
    createdAt: null, // serverTimestamp() in production; processInput() does not read it
    startedAt: null,
    completedAt: null,
    leaseExpiresAt: null,
    attemptCount: 0,
    maxAttempts: 3,
    processingVersion: PROCESSING_VERSION,
    ocrRequested: false,
    ocrUsed: false,
    webhookUrl: null,
    webhookSecret: null,
    ocr: {
      requested: false,
      used: false,
      provider: "none",
      status: "not_requested",
      pageCount: null,
      costEstimateUsd: null,
      reason: "OCR was not requested for this job."
    },
    ocrMonthlyLimit: FREE_PLAN.monthlyOcrPageLimit,
    ocrPageLimitPerJob: FREE_PLAN.maxOcrPagesPerJob,
    ocrUsageId: null,
    ocrMonthKey: null,
    plan: FREE_PLAN.plan,
    dailyConversionLimit: FREE_PLAN.dailyConversionLimit,
    maxActiveJobs: FREE_PLAN.maxActiveJobs,
    originalTokenEstimate: null,
    optimizedTokenEstimate: null,
    savingsPercent: null,
    pageCount: null,
    sectionCount: null,
    tableCount: null,
    imageCount: null,
    outputPath: null,
    zipPath: null,
    errorCode: null,
    errorMessage: null,
    processingNotes: [],
    usageLimitId: `${BENCH_USER_ID}_${now.toISOString().slice(0, 10)}`,
    retentionExpiresAt: null // a Timestamp 7 days ahead in production; processInput() does not read it
  };
  // claimQueuedJob() in services/worker/src/jobs.ts hands this to processJob() and processInput().
  return { ...queued, jobId, status: "processing", ocrReservedPages: 0, attemptCount: queued.attemptCount + 1 };
}

/**
 * Makes every way out of this process throw: fetch, sockets (net, tls, http, https, http2, node-fetch, gRPC),
 * DNS, UDP, child processes and worker threads. Returns the list that records each attempt.
 */
export function installNetworkGuards() {
  const require = createRequire(import.meta.url);
  const attempts = [];
  const block = (kind, target) => {
    const detail = describeTarget(target);
    attempts.push({ kind, target: detail });
    const error = new Error(`run-packforai blocked ${kind} (${detail}): the benchmark runner never uses the network or cloud services.`);
    error.code = "PACKFORAI_BENCH_BLOCKED";
    return error;
  };

  globalThis.fetch = function fetchBlockedByBenchmark(input) {
    throw block("fetch", input);
  };
  for (const name of ["WebSocket", "EventSource"]) {
    if (name in globalThis) {
      Object.defineProperty(globalThis, name, {
        configurable: true,
        enumerable: false,
        writable: true,
        value: function blockedByBenchmark(url) {
          throw block(name, url);
        }
      });
    }
  }

  const net = require("node:net");
  net.Socket.prototype.connect = function connectBlockedByBenchmark(...args) {
    throw block("socket connect", args[0]);
  };

  const dns = require("node:dns");
  const dnsMethods = [
    "lookup", "lookupService", "resolve", "resolve4", "resolve6", "resolveAny", "resolveCaa", "resolveCname",
    "resolveMx", "resolveNaptr", "resolveNs", "resolvePtr", "resolveSoa", "resolveSrv", "resolveTlsa",
    "resolveTxt", "reverse"
  ];
  for (const target of [dns, dns.Resolver.prototype]) {
    for (const name of dnsMethods) {
      if (typeof target[name] === "function") {
        target[name] = function dnsBlockedByBenchmark(host) {
          throw block(`dns.${name}`, host);
        };
      }
    }
  }
  for (const target of [dns.promises, dns.promises.Resolver.prototype]) {
    for (const name of dnsMethods) {
      if (typeof target[name] === "function") {
        target[name] = async function dnsBlockedByBenchmark(host) {
          throw block(`dns.promises.${name}`, host);
        };
      }
    }
  }

  const dgram = require("node:dgram");
  dgram.createSocket = function udpBlockedByBenchmark(type) {
    throw block("UDP socket", type);
  };

  const childProcess = require("node:child_process");
  for (const name of ["exec", "execFile", "execFileSync", "execSync", "fork", "spawn", "spawnSync"]) {
    childProcess[name] = function childProcessBlockedByBenchmark(command) {
      throw block(`child_process.${name}`, command);
    };
  }

  const workerThreads = require("node:worker_threads");
  workerThreads.Worker = function WorkerBlockedByBenchmark(file) {
    throw block("worker thread", file);
  };

  // ES module imports of these built-ins (import { lookup } from "node:dns") see the replacements too.
  syncBuiltinESMExports();
  return attempts;
}

// ---------------------------------------------------------------------------------------------------------
// Parent: lists the inputs, keeps one conversion process alive, writes the JSON results.

async function main(argv) {
  if (argv[0] === "--child") {
    await runChild();
    return;
  }
  // The parent only lists files, runs git and writes results; it has no reason to fetch anything either.
  globalThis.fetch = function fetchBlockedByBenchmark() {
    throw new Error("run-packforai never uses the network.");
  };
  if (argv.length !== 2 || argv.some((arg) => arg.startsWith("-"))) {
    process.stderr.write(USAGE);
    process.exitCode = 2;
    return;
  }

  const inputDir = path.resolve(argv[0]);
  const outDir = path.resolve(argv[1]);
  if (!statSync(inputDir, { throwIfNoEntry: false })?.isDirectory()) {
    return setupError(`Input folder not found: ${argv[0]}`);
  }
  if (!existsSync(PROCESSOR_FILE)) {
    return setupError(`${repoPath(PROCESSOR_FILE)} is missing. Build the worker first: cd aireadydoc/services/worker && npm run build`);
  }
  await mkdir(outDir, { recursive: true });
  if (realpathSync(inputDir) === realpathSync(outDir)) {
    return setupError("<outDir> must differ from <inputDir>: the .json results would be read as inputs on the next run.");
  }

  const startedAt = new Date().toISOString();
  const meta = collectRunMetadata();
  const listing = await listInputs(inputDir);
  const scrubRoots = [[inputDir, "<inputDir>"], [outDir, "<outDir>"]];

  console.log("PackForAI benchmark runner");
  console.log(`  worker   ${meta.workerGitCommit ?? "unknown commit"}${meta.gitDirtyPaths.length ? " (uncommitted changes, see run.worker.gitDirtyPaths)" : ""}`);
  console.log(`  dist     ${repoPath(PROCESSOR_FILE)} sha256:${meta.workerDistSha256.slice(0, 16)}`);
  console.log(`  input    ${inputDir}: ${listing.files.length} file(s)${listing.skippedFolders.length ? `; skipped folders: ${listing.skippedFolders.join(", ")}` : ""}${listing.skippedHidden ? `; skipped ${listing.skippedHidden} hidden` : ""}${listing.skippedOther.length ? `; skipped (not a regular file): ${listing.skippedOther.join(", ")}` : ""}`);
  console.log(`  output   ${outDir}`);
  for (const warning of meta.warnings) console.warn(`  warning  ${warning}`);

  const converter = new ConversionProcess(scrubRoots);
  try {
    await converter.start();
  } catch (error) {
    return setupError(`The conversion process did not start: ${error instanceof Error ? error.message : String(error)}`);
  }
  console.log(`  node     ${converter.ready.runtime.nodeVersion} (production: ${PRODUCTION_RUNTIME})`);
  console.log(`  warm-up  ${converter.ready.warmup.ms} ms (${Object.entries(converter.ready.warmup.results).map(([type, result]) => `${type} ${result}`).join(", ")})`);

  const counts = { converted: 0, failed: 0, rejected: 0 };
  let aborted = null;
  for (const [index, entry] of listing.files.entries()) {
    const inputPath = path.join(inputDir, entry.name);
    let bytes = null;
    let contentHash = null;
    let readError = null;
    try {
      const content = await readFile(inputPath);
      bytes = content.length;
      contentHash = sha256(content);
    } catch (error) {
      readError = error;
    }
    const admission = classifyUpload(entry.name, bytes ?? entry.size);

    let reply;
    if (readError) {
      reply = { ok: false, error: { code: "READ_ERROR", ...describeError(readError, scrubRoots) } };
    } else if (admission.rejection) {
      reply = { ok: false, error: { ...admission.rejection, rejectedByProduction: true } };
    } else if (aborted) {
      reply = { ok: false, error: { code: "RUNNER_ERROR", message: aborted } };
    } else {
      try {
        reply = await converter.convert({
          inputPath,
          name: entry.name,
          outDir,
          fileName: admission.fileName,
          fileType: admission.fileType
        });
      } catch (error) {
        aborted = `The conversion process could not be restarted: ${error instanceof Error ? error.message : String(error)}`;
        reply = { ok: false, error: { code: "RUNNER_ERROR", message: aborted } };
      }
      if (reply.ok && reply.input?.sha256 !== contentHash) {
        reply = { ...reply, ok: false, error: { code: "INPUT_CHANGED", message: "The file changed while it was being converted." } };
      }
    }

    if (!reply.ok) await removeOutputs(outDir, entry.name, reply.childPid);
    const record = buildRecord({ entry, admission, bytes, contentHash, reply, meta, startedAt, inputDir, converter });
    await writeTextAtomic(path.join(outDir, `${entry.name}.packforai.json`), `${JSON.stringify(record, null, 2)}\n`);

    if (reply.ok) counts.converted += 1;
    else if (admission.rejectedByProduction) counts.rejected += 1;
    else counts.failed += 1;
    console.log(progressLine(index, listing.files.length, entry.name, admission, record));
  }
  await converter.close();

  // Results left by an earlier run for files that are no longer inputs are kept, but named, so they are not
  // scored by mistake.
  const current = new Set(listing.files.map((entry) => entry.name));
  const leftovers = (await readdir(outDir))
    .map((name) => /^(.+)\.packforai\.(?:document\.md|compact\.md|json)$/.exec(name))
    .filter((match) => match && !current.has(match[1]) && !match[1].startsWith("."))
    .map((match) => match[0])
    .sort(compareNames);
  if (leftovers.length) {
    console.warn(`  warning  ${leftovers.length} result file(s) in <outDir> belong to no current input (left by an earlier run): ${leftovers.slice(0, 10).join(", ")}${leftovers.length > 10 ? ", …" : ""}`);
  }

  console.log(`Done: ${counts.converted} converted, ${counts.failed} failed, ${counts.rejected} rejected by production upload rules. Results: ${outDir}`);
  if (aborted) {
    console.error(aborted);
    process.exitCode = 2;
  }
}

function setupError(message) {
  console.error(`run-packforai: ${message}`);
  process.exitCode = 2;
}

async function listInputs(inputDir) {
  const files = [];
  const skippedFolders = [];
  const skippedOther = [];
  let skippedHidden = 0;
  for (const name of (await readdir(inputDir)).sort(compareNames)) {
    if (name.startsWith(".")) {
      skippedHidden += 1;
      continue;
    }
    const info = await stat(path.join(inputDir, name)).catch(() => null);
    if (info?.isDirectory()) skippedFolders.push(`${name}/`);
    else if (info?.isFile()) files.push({ name, size: info.size });
    else skippedOther.push(name);
  }
  return { files, skippedFolders, skippedOther, skippedHidden };
}

function collectRunMetadata() {
  const warnings = [];
  const git = (args) => {
    try {
      return execFileSync("git", args, {
        cwd: WORKER_DIR,
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
        timeout: 20_000
      }).trim();
    } catch (error) {
      warnings.push(`git ${args[0]} failed: ${String(error?.message ?? error).split("\n")[0]}`);
      return null;
    }
  };
  const workerGitCommit = git(["rev-parse", "HEAD"]);
  const status = git(["status", "--porcelain", "--untracked-files=all", "--", ...WATCHED_SOURCE_PATHS]);
  const gitDirtyPaths = status ? status.split("\n").filter(Boolean) : [];
  if (gitDirtyPaths.length) warnings.push(`uncommitted changes in files that shape the conversion: ${gitDirtyPaths.join("; ")}`);

  // dist/ is git-ignored, so the commit alone does not prove which code ran.
  const distFiles = readdirSync(DIST_DIR).filter((name) => name.endsWith(".js")).sort(compareNames);
  const distHash = createHash("sha256");
  for (const name of distFiles) {
    distHash.update(name).update("\0").update(readFileSync(path.join(DIST_DIR, name))).update("\0");
  }
  const sourceDir = path.join(WORKER_DIR, "src");
  const distPossiblyStale = readdirSync(sourceDir)
    .filter((name) => name.endsWith(".ts") && !name.endsWith(".d.ts"))
    .filter((name) => {
      const compiled = path.join(DIST_DIR, name.replace(/\.ts$/, ".js"));
      return !existsSync(compiled) || statSync(path.join(sourceDir, name)).mtimeMs > statSync(compiled).mtimeMs;
    });
  if (distPossiblyStale.length) {
    warnings.push(`dist/ may be older than src/ (${distPossiblyStale.join(", ")}): run npm run build in aireadydoc/services/worker`);
  }

  let lockfile = {};
  try {
    lockfile = JSON.parse(readFileSync(path.join(REPO_ROOT, "package-lock.json"), "utf8")).packages ?? {};
  } catch {
    warnings.push("package-lock.json could not be read; dependency versions are not compared with it");
  }
  const dependencies = {};
  for (const name of RECORDED_PACKAGES) {
    const dir = findPackageDir(name);
    const installed = dir ? JSON.parse(readFileSync(path.join(dir, "package.json"), "utf8")).version : null;
    const locked =
      lockfile[`aireadydoc/services/worker/node_modules/${name}`]?.version ?? lockfile[`node_modules/${name}`]?.version ?? null;
    dependencies[name] = { installed, lockfile: locked };
    if (installed !== locked) warnings.push(`${name} ${installed ?? "missing"} is installed but package-lock.json (what production installs) has ${locked ?? "nothing"}`);
  }

  return {
    workerGitCommit,
    gitDirtyPaths,
    workerDistSha256: distHash.digest("hex"),
    distPossiblyStale,
    dependencies,
    runnerSha256: sha256(readFileSync(RUNNER_FILE)),
    warnings
  };
}

function buildRecord({ entry, admission, bytes, contentHash, reply, meta, startedAt, inputDir, converter }) {
  const ok = reply.ok === true;
  const ready = reply.ready ?? converter.ready;
  return {
    schema: SCHEMA,
    tool: "PackForAI",
    file: entry.name,
    ok,
    error: ok ? null : reply.error,
    input: { fileName: admission.fileName, fileType: admission.fileType, bytes, sha256: contentHash },
    outputs: ok ? reply.outputs : null,
    tokenAnalysis: ok ? reply.tokenAnalysis : null,
    textQuality: ok ? reply.textQuality : null,
    processingNotes: ok ? reply.processingNotes : null,
    ocr: ok ? reply.ocr : null,
    stats: ok ? reply.stats : null,
    elapsedMs: reply.elapsedMs ?? null,
    workerGitCommit: meta.workerGitCommit,
    nodeVersion: ready?.runtime?.nodeVersion ?? null,
    admission: {
      rejectedByProduction: admission.rejectedByProduction,
      freePlanUpload: admission.freePlanUpload,
      notes: admission.notes
    },
    job: reply.job ?? null,
    isolation: {
      networkAttempts: reply.networkAttempts ?? [],
      consoleOutput: reply.consoleOutput ?? { lines: [], total: 0 }
    },
    run: {
      startedAt,
      runner: repoPath(RUNNER_FILE),
      runnerSha256: meta.runnerSha256,
      inputFolder: path.basename(inputDir),
      worker: {
        processor: repoPath(PROCESSOR_FILE),
        distSha256: meta.workerDistSha256,
        distPossiblyStale: meta.distPossiblyStale,
        gitDirtyPaths: meta.gitDirtyPaths
      },
      dependencies: meta.dependencies,
      runtime: ready?.runtime ?? null,
      productionRuntime: PRODUCTION_RUNTIME,
      timing: TIMING_NOTE,
      warmup: ready?.warmup ?? null,
      fileTimeoutMs: FILE_TIMEOUT_MS,
      conversionProcess: reply.childPid ? { pid: reply.childPid, start: reply.childStart } : null
    }
  };
}

function progressLine(index, total, name, admission, record) {
  const counter = `[${String(index + 1).padStart(String(total).length)}/${total}]`;
  const type = (admission.fileType ?? "-").padEnd(4);
  if (record.ok) {
    const ms = `${record.elapsedMs.toFixed(1)} ms`.padStart(11);
    return `${counter} ok     ${type} ${ms}  document ${record.outputs.document.tokensO200k} tok  compact ${record.outputs.compact.tokensO200k} tok  ${name}`;
  }
  const status = admission.rejectedByProduction ? "reject" : "FAIL  ";
  return `${counter} ${status} ${type} ${record.error.code}: ${String(record.error.message).split("\n")[0].slice(0, 160)}  ${name}`;
}

async function removeOutputs(outDir, name, childPid) {
  const names = [`${name}.packforai.document.md`, `${name}.packforai.compact.md`];
  if (childPid) names.push(...names.map((file) => `.${file}.tmp-${childPid}`));
  await Promise.all(names.map((file) => rm(path.join(outDir, file), { force: true })));
}

/** One long-lived conversion process; a new one replaces it after a timeout or a crash. */
class ConversionProcess {
  constructor(scrubRoots) {
    this.scrubRoots = scrubRoots;
    this.handle = null;
    this.ready = null;
    this.starts = 0;
    this.nextId = 0;
  }

  async start() {
    this.starts += 1;
    const handle = spawnChild();
    this.handle = handle;
    const first = await handle.wait(STARTUP_TIMEOUT_MS);
    if (first.type !== "ready") {
      handle.kill();
      this.handle = null;
      const reason =
        first.type === "fatal" ? `${first.code}: ${first.message}`
          : first.type === "timeout" ? `no answer within ${STARTUP_TIMEOUT_MS / 1000} s`
            : `it exited (code ${first.code}, signal ${first.signal})`;
      throw new Error(`${reason}${handle.stderrTail() ? `\n${handle.stderrTail()}` : ""}`);
    }
    this.ready = first;
  }

  async convert(task) {
    if (!this.handle || this.handle.exited || !this.handle.child.connected) await this.start();
    const handle = this.handle;
    const id = ++this.nextId;
    const reply = handle.wait(FILE_TIMEOUT_MS);
    try {
      handle.child.send({ type: "convert", id, ...task });
    } catch {
      // The process died between files: the wait below reports the exit.
    }
    const message = await reply;
    const context = { childPid: handle.child.pid, childStart: this.starts, ready: this.ready };
    if (message.type === "done" && message.id === id) return { ...message, ...context };

    handle.kill();
    this.handle = null;
    if (message.type === "timeout") {
      return {
        ok: false,
        ...context,
        error: { code: "TIMEOUT", message: `No result within ${FILE_TIMEOUT_MS / 1000} s, so the conversion was stopped.` }
      };
    }
    return {
      ok: false,
      ...context,
      error: {
        code: "CONVERSION_PROCESS_EXITED",
        message: message.type === "exit"
          ? `The conversion process exited (code ${message.code}, signal ${message.signal}) before it returned a result.`
          : `Unexpected message from the conversion process: ${JSON.stringify(message).slice(0, 200)}`,
        stderrTail: scrub(handle.stderrTail(), this.scrubRoots) || null
      }
    };
  }

  async close() {
    const handle = this.handle;
    this.handle = null;
    if (!handle || handle.exited) return;
    const exited = handle.wait(5_000);
    try {
      handle.child.send({ type: "exit" });
    } catch {
      // Already gone.
    }
    if ((await exited).type === "timeout") handle.kill();
  }
}

function spawnChild() {
  const child = fork(RUNNER_FILE, ["--child"], {
    cwd: REPO_ROOT, // the image runs the worker from /app, the repository root
    env: childEnvironment(),
    stdio: ["ignore", "pipe", "pipe", "ipc"]
  });
  let tail = "";
  let waiter = null;
  const handle = {
    child,
    exited: null,
    stderrTail: () => tail.trim(),
    kill() {
      if (!handle.exited) child.kill("SIGKILL");
    },
    wait(timeoutMs) {
      return new Promise((resolve) => {
        if (handle.exited) {
          resolve(handle.exited);
          return;
        }
        const timer = setTimeout(() => {
          waiter = null;
          resolve({ type: "timeout" });
        }, timeoutMs);
        waiter = (message) => {
          clearTimeout(timer);
          waiter = null;
          resolve(message);
        };
      });
    }
  };
  const settle = (message) => waiter?.(message);
  child.stdout.on("data", (chunk) => process.stdout.write(chunk));
  child.stderr.on("data", (chunk) => {
    process.stderr.write(chunk);
    tail = (tail + chunk.toString("utf8")).slice(-4000);
  });
  child.on("message", settle);
  child.on("error", (error) => {
    handle.exited ??= { type: "exit", code: null, signal: null, error: String(error?.message ?? error) };
    settle(handle.exited);
  });
  child.on("exit", (code, signal) => {
    handle.exited ??= { type: "exit", code, signal };
    settle(handle.exited);
  });
  return handle;
}

/** The parent's environment without cloud settings, with the production container's NODE_ENV and clock. */
function childEnvironment() {
  const env = { ...process.env };
  const cloudSetting = /^(GOOGLE_|GCLOUD_|GCE_|GCP_|CLOUDSDK_|FIREBASE_|FIRESTORE_|STORAGE_EMULATOR_HOST$|DOCUMENT_AI_|OCR_|WORKER_SHARED_SECRET$|K_SERVICE$|K_REVISION$|K_CONFIGURATION$|CLOUD_RUN_)/;
  const locale = /^(LANG|LANGUAGE|LC_[A-Z]+)$/;
  for (const key of Object.keys(env)) {
    if (cloudSetting.test(key) || locale.test(key)) delete env[key];
  }
  env.GOOGLE_APPLICATION_CREDENTIALS = "/nonexistent/packforai-benchmark/no-credentials.json";
  env.CLOUDSDK_CONFIG = "/nonexistent/packforai-benchmark/gcloud";
  env.METADATA_SERVER_DETECTION = "none";
  env.NODE_ENV = "production";
  env.TZ = "UTC";
  return env;
}

// ---------------------------------------------------------------------------------------------------------
// Conversion process.

async function runChild() {
  const attempts = installNetworkGuards();
  const capture = installConsoleCapture();
  let current = null;

  const crash = (code, error) => {
    const detail = describeError(error, current?.scrubRoots ?? []);
    try {
      process.stderr.write(`run-packforai conversion process: ${code}: ${detail.message}\n`);
    } catch {
      // stderr is gone.
    }
    const message = current
      ? {
          type: "done",
          id: current.id,
          ok: false,
          error: { code, ...detail },
          networkAttempts: attempts.slice(current.attemptsBefore),
          consoleOutput: capture.stop()
        }
      : { type: "fatal", code, message: detail.message };
    setTimeout(() => process.exit(70), 2_000).unref();
    if (process.connected) process.send(message, () => process.exit(70));
    else process.exit(70);
  };
  process.on("uncaughtException", (error) => crash("UNCAUGHT_EXCEPTION", error));
  process.on("unhandledRejection", (reason) => crash("UNHANDLED_REJECTION", reason));
  process.on("disconnect", () => process.exit(0));

  let worker;
  try {
    worker = await loadWorker();
  } catch (error) {
    process.send({ type: "fatal", code: "IMPORT_FAILED", message: describeError(error).message }, () => process.exit(1));
    return;
  }
  if (attempts.length) {
    process.send({ type: "fatal", code: "NETWORK_ON_IMPORT", message: `Importing the worker tried to reach: ${JSON.stringify(attempts)}` }, () => process.exit(1));
    return;
  }

  const warmup = await warmUp(worker, capture);
  if (attempts.length) {
    process.send({ type: "fatal", code: "NETWORK_ON_WARMUP", message: `The warm-up conversions tried to reach: ${JSON.stringify(attempts)}` }, () => process.exit(1));
    return;
  }

  process.on("message", (message) => {
    if (message?.type === "exit") process.exit(0);
    if (message?.type !== "convert") return;
    const scrubRoots = [[path.dirname(message.inputPath), "<inputDir>"], [message.outDir, "<outDir>"]];
    current = { id: message.id, attemptsBefore: attempts.length, scrubRoots };
    convertOne(worker, message, attempts, capture, scrubRoots).then((reply) => {
      current = null;
      process.send(reply);
    });
  });
  process.send({ type: "ready", pid: process.pid, warmup, runtime: runtimeInfo(worker) });
}

async function loadWorker() {
  const { processInput } = await import(PROCESSOR_URL.href);
  // The worker's tokens.js imports "gpt-tokenizer/encoding/o200k_base", which resolves to this file.
  const tokenizerDir = findPackageDir("gpt-tokenizer");
  const tokenizerFile = tokenizerDir ? path.join(tokenizerDir, "esm", "encoding", "o200k_base.js") : null;
  if (!tokenizerFile || !existsSync(tokenizerFile)) throw new Error("gpt-tokenizer (o200k_base) is not installed next to the worker.");
  const { countTokens } = await import(pathToFileURL(tokenizerFile).href);
  const fflate = createRequire(PROCESSOR_FILE)("fflate");
  return { processInput, countTokens, fflate, tokenizerFile };
}

function runtimeInfo(worker) {
  const intl = Intl.DateTimeFormat().resolvedOptions();
  return {
    nodeVersion: process.version,
    v8: process.versions.v8,
    icu: process.versions.icu ?? null,
    unicode: process.versions.unicode ?? null,
    platform: `${process.platform}-${process.arch}`,
    nodeEnv: process.env.NODE_ENV ?? null,
    timeZone: intl.timeZone,
    locale: intl.locale,
    tokenizer: `o200k_base via ${repoPath(worker.tokenizerFile)}`
  };
}

async function warmUp(worker, capture) {
  const started = performance.now();
  const results = {};
  capture.start();
  for (const [fileType, bytes] of Object.entries(warmUpSamples(worker.fflate))) {
    const fileName = `warm-up.${fileType}`;
    const job = buildProductionJob({ fileName, fileType, fileSize: bytes.length, sha256: sha256(bytes) });
    try {
      const output = await worker.processInput(job, bytes);
      worker.countTokens(output.files.markdown, { disallowedSpecial: new Set() });
      results[fileType] = "ok";
    } catch (error) {
      results[fileType] = `failed: ${describeError(error).message.slice(0, 200)}`;
    }
  }
  const consoleOutput = capture.stop();
  return { ms: round(performance.now() - started), results, consoleLines: consoleOutput.total };
}

async function convertOne(worker, task, attempts, capture, scrubRoots) {
  const base = { type: "done", id: task.id };
  const attemptsBefore = attempts.length;
  let input;
  try {
    const raw = await readFile(task.inputPath);
    // processJob() downloads the upload as Buffer.from(await response.arrayBuffer()): a Buffer over its own ArrayBuffer.
    input = Buffer.from(raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength));
  } catch (error) {
    return { ...base, ok: false, error: { code: "READ_ERROR", ...describeError(error, scrubRoots) } };
  }
  const inputInfo = { bytes: input.length, sha256: sha256(input) };
  const job = buildProductionJob({ fileName: task.fileName, fileType: task.fileType, fileSize: input.length, sha256: inputInfo.sha256 });

  let output;
  let failure = null;
  capture.start();
  const started = performance.now();
  try {
    output = await worker.processInput(job, input);
  } catch (error) {
    failure = error;
  }
  const elapsedMs = round(performance.now() - started);
  const consoleOutput = capture.stop();
  const networkAttempts = attempts.slice(attemptsBefore);
  const common = { ...base, input: inputInfo, job, elapsedMs, networkAttempts, consoleOutput };

  if (networkAttempts.length) {
    return {
      ...common,
      ok: false,
      error: {
        code: "NETWORK_ATTEMPT",
        message: `The conversion tried to reach ${networkAttempts.map((attempt) => attempt.kind).join(", ")}; the result is discarded because a production run would not have matched it.`,
        ...(failure ? { conversionError: describeError(failure, scrubRoots).message } : {})
      }
    };
  }
  if (failure) return { ...common, ok: false, error: { code: "CONVERSION_ERROR", ...describeError(failure, scrubRoots) } };

  try {
    const documentFile = `${task.name}.packforai.document.md`;
    const compactFile = `${task.name}.packforai.compact.md`;
    await writeTextAtomic(path.join(task.outDir, documentFile), output.files.markdown);
    await writeTextAtomic(path.join(task.outDir, compactFile), output.files.compactMarkdown);
    return {
      ...common,
      ok: true,
      outputs: {
        document: describeOutput(worker, documentFile, output.files.markdown),
        compact: describeOutput(worker, compactFile, output.files.compactMarkdown)
      },
      tokenAnalysis: output.tokenAnalysis,
      textQuality: output.textQuality,
      processingNotes: output.extracted.processingNotes,
      ocr: output.ocr,
      stats: output.extracted.stats
    };
  } catch (error) {
    return { ...common, ok: false, error: { code: "WRITE_ERROR", ...describeError(error, scrubRoots) } };
  }
}

/**
 * Size of one written output, counted like score.mjs: the text as stored, Unicode code points, UTF-8 bytes and
 * o200k_base tokens with strings such as "<|endoftext|>" counted as ordinary text (tiktoken's
 * disallowed_special=()). A counting failure is recorded and never fails the conversion.
 */
function describeOutput(worker, file, text) {
  let tokensO200k = null;
  let tokenCountError = null;
  try {
    tokensO200k = worker.countTokens(text, { disallowedSpecial: new Set() });
  } catch (error) {
    tokenCountError = describeError(error).message;
  }
  return {
    file,
    bytes: Buffer.byteLength(text, "utf8"),
    codePoints: [...text].length,
    sha256: sha256(text),
    tokensO200k,
    ...(tokenCountError ? { tokenCountError } : {})
  };
}

/** Collects what the libraries print (pdf.js warnings, mammoth messages) while a conversion runs. */
function installConsoleCapture() {
  const methods = ["log", "info", "warn", "error", "debug", "trace"];
  const original = Object.fromEntries(methods.map((method) => [method, console[method].bind(console)]));
  let lines = null;
  let total = 0;
  for (const method of methods) {
    console[method] = (...args) => {
      if (!lines) {
        original[method](...args);
        return;
      }
      total += 1;
      if (lines.length < MAX_CONSOLE_LINES) lines.push(`${method}: ${scrub(format(...args)).slice(0, 500)}`);
    };
  }
  return {
    start() {
      lines = [];
      total = 0;
    },
    stop() {
      const result = { lines: lines ?? [], total };
      lines = null;
      return result;
    }
  };
}

/** One small file per type, so the timed conversions run on warm code like a long-lived worker instance. */
function warmUpSamples({ zipSync, strToU8 }) {
  const zip = (files) => Buffer.from(zipSync(Object.fromEntries(Object.entries(files).map(([name, text]) => [name, strToU8(text)]))));
  const sml = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
  const rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
  const pml = "http://schemas.openxmlformats.org/presentationml/2006/main";
  const dml = "http://schemas.openxmlformats.org/drawingml/2006/main";
  const wml = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
  const run = (text) => `<w:p><w:r><w:t>${text}</w:t></w:r></w:p>`;
  return {
    pdf: minimalPdf(["Warm-up report", "Item    Quantity    Price", "Bolts    12    3.50"]),
    docx: zip({
      "word/document.xml": `<w:document xmlns:w="${wml}"><w:body>${run("Warm-up document")}${run("A short paragraph.")}<w:tbl><w:tr><w:tc>${run("Item")}</w:tc><w:tc>${run("Qty")}</w:tc></w:tr><w:tr><w:tc>${run("Bolt")}</w:tc><w:tc>${run("12")}</w:tc></w:tr></w:tbl></w:body></w:document>`
    }),
    pptx: zip({
      "ppt/slides/slide1.xml": `<p:sld xmlns:p="${pml}" xmlns:a="${dml}"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Warm-up slide</a:t></a:r></a:p><a:p><a:r><a:t>First point</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>`
    }),
    xlsx: zip({
      "xl/workbook.xml": `<workbook xmlns="${sml}" xmlns:r="${rel}"><sheets><sheet name="Warm-up" sheetId="1" r:id="rId1"/></sheets></workbook>`,
      "xl/_rels/workbook.xml.rels": `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${rel}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>`,
      "xl/worksheets/sheet1.xml": `<worksheet xmlns="${sml}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Item</t></is></c><c r="B1" t="inlineStr"><is><t>Qty</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Bolt</t></is></c><c r="B2"><v>12</v></c></row></sheetData></worksheet>`
    }),
    csv: Buffer.from("Item,Qty,Price\nBolt,12,3.50\nNut,40,0.20\n"),
    json: Buffer.from('[{"item":"Bolt","qty":12},{"item":"Nut","qty":40}]')
  };
}

/** A valid one-page PDF with Helvetica text lines and a correct cross-reference table. */
function minimalPdf(lines) {
  const escape = (text) => text.replace(/[\\()]/g, "\\$&");
  const content = `BT /F1 12 Tf 36 140 Td 16 TL ${lines.map((line) => `(${escape(line)}) Tj T*`).join(" ")} ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 180] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
    `<< /Length ${Buffer.byteLength(content, "latin1")} >>\nstream\n${content}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = objects.map((body, index) => {
    const offset = Buffer.byteLength(pdf, "latin1");
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`;
    return offset;
  });
  const xref = Buffer.byteLength(pdf, "latin1");
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("")}`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(pdf, "latin1");
}

// ---------------------------------------------------------------------------------------------------------
// Helpers.

async function writeTextAtomic(file, text) {
  const temporary = path.join(path.dirname(file), `.${path.basename(file)}.tmp-${process.pid}`);
  await writeFile(temporary, text, "utf8");
  await rename(temporary, file);
}

function findPackageDir(name) {
  for (let dir = WORKER_DIR; ; dir = path.dirname(dir)) {
    const candidate = path.join(dir, "node_modules", name);
    if (existsSync(path.join(candidate, "package.json"))) return candidate;
    if (path.dirname(dir) === dir) return null;
  }
}

function describeError(error, scrubRoots = []) {
  const message = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error && typeof error.stack === "string" ? error.stack.split("\n").slice(0, 12).join("\n") : null;
  return {
    name: error instanceof Error ? error.name : typeof error,
    message: scrub(message, scrubRoots),
    stack: stack ? scrub(stack, scrubRoots) : null
  };
}

function describeTarget(value) {
  try {
    if (value === undefined || value === null) return "";
    if (typeof value === "string" || typeof value === "number") return String(value).slice(0, 200);
    if (value instanceof URL) return value.href.slice(0, 200);
    if (typeof value.url === "string") return value.url.slice(0, 200);
    if (typeof value === "object") {
      return JSON.stringify({ host: value.host ?? value.hostname, port: value.port, path: value.path }).slice(0, 200);
    }
    return String(value).slice(0, 200);
  } catch {
    return "?";
  }
}

/** Replaces local absolute paths so results can be shared without revealing the machine's folders. */
function scrub(text, roots = []) {
  let result = String(text ?? "");
  for (const [root, label] of [...roots, [REPO_ROOT, "<repo>"], [os.homedir(), "~"]]) {
    if (root && root.length > 1) result = result.split(root).join(label);
  }
  return result;
}

function repoPath(file) {
  const relative = path.relative(REPO_ROOT, file);
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative) ? relative.split(path.sep).join("/") : scrub(file);
}

function sha256(data) {
  return createHash("sha256").update(data).digest("hex");
}

function round(ms) {
  return Math.round(ms * 1000) / 1000;
}

function compareNames(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function readPositiveInt(name, fallback) {
  const value = Number(process.env[name]);
  return Number.isSafeInteger(value) && value > 0 ? value : fallback;
}

const isEntryPoint = (() => {
  try {
    return Boolean(process.argv[1]) && realpathSync(process.argv[1]) === realpathSync(RUNNER_FILE);
  } catch {
    return false;
  }
})();

if (isEntryPoint) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(`run-packforai: ${error instanceof Error ? error.stack : String(error)}`);
    process.exitCode = 2;
  });
}
