The NIST Cybersecurity
Framework (CSF) 2.0

National Institute of Standards and Technology
This publication is available free of charge from: https://doi.org/10.6028/NIST.CSWP.29

February 26, 2024

NIST CSWP 29
February 26, 2024

Abstract

The NIST Cybersecurity Framework (CSF) 2.0

The NIST Cybersecurity Framework (CSF) 2.0 provides guidance to industry, government
agencies, and other organizations to manage cybersecurity risks. It offers a taxonomy of high-
level cybersecurity outcomes that can be used by any organization — regardless of its size,
sector, or maturity — to better understand, assess, prioritize, and communicate its
cybersecurity efforts. The CSF does not prescribe how outcomes should be achieved. Rather, it
links to online resources that provide additional guidance on practices and controls that could
be used to achieve those outcomes. This document describes CSF 2.0, its components, and
some of the many ways that it can be used.

Keywords

cybersecurity; Cybersecurity Framework (CSF); cybersecurity risk governance; cybersecurity risk
management; enterprise risk management; Profiles; Tiers.

Audience

Individuals responsible for developing and leading cybersecurity programs are the primary
audience for the CSF. The CSF can also be used by others involved in managing risk — including
executives, boards of directors, acquisition professionals, technology professionals, risk
managers, lawyers, human resources specialists, and cybersecurity and risk management
auditors — to guide their cybersecurity-related decisions. Additionally, the CSF can be useful to
those making and influencing policy (e.g., associations, professional organizations, regulators)
who set and communicate priorities for cybersecurity risk management.

Supplemental Content

NIST will continue to build and host additional resources to help organizations implement the
CSF, including Quick Start Guides and Community Profiles. All resources are made publicly
available on the NIST CSF website. Suggestions for additional resources to reference on the
NIST CSF website can always be shared with NIST at cyberframework@nist.gov.

Note to Readers

Unless otherwise noted, documents cited, referenced, or excerpted in this publication are not
wholly incorporated into this publication.

Before version 2.0, the Cybersecurity Framework was called the “Framework for Improving
Critical Infrastructure Cybersecurity.” This title is not used for CSF 2.0.

 i

NIST CSWP 29
February 26, 2024

Acknowledgments

The NIST Cybersecurity Framework (CSF) 2.0

The CSF is the result of a multi-year collaborative effort across industry, academia, and
government in the United States and around the world. NIST acknowledges and thanks all of
those who have contributed to this revised CSF. Information on the CSF development process
can be found on the NIST CSF website. Lessons learned about the use of the CSF can always be
shared with NIST at cyberframework@nist.gov.

 ii

NIST CSWP 29
February 26, 2024

Table of Contents

The NIST Cybersecurity Framework (CSF) 2.0

1. Cybersecurity Framework (CSF) Overview .......................................................................................1

2. Introduction to the CSF Core ...........................................................................................................3

3. Introduction to CSF Profiles and Tiers .............................................................................................6

4. Introduction to Online Resources That Supplement the CSF ............................................................9

5. Improving Cybersecurity Risk Communication and Integration ...................................................... 10

Appendix A. CSF Core ....................................................................................................................... 15

Appendix B. CSF Tiers ....................................................................................................................... 24

Appendix C. Glossary ....................................................................................................................... 26

List of Figures

Fig. 1. CSF Core structure ....................................................................................................................3

Fig. 2. CSF Functions ...........................................................................................................................5

Fig. 3. Steps for creating and using a CSF Organizational Profile ...........................................................6

Fig. 4. CSF Tiers for cybersecurity risk governance and management ...................................................8

Fig. 5. Using the CSF to improve risk management communication .................................................... 10

Fig. 6. Cybersecurity and privacy risk relationship ............................................................................. 13

 iii

NIST CSWP 29
February 26, 2024

Preface

The NIST Cybersecurity Framework (CSF) 2.0

The Cybersecurity Framework (CSF) 2.0 is designed to help organizations of all sizes and sectors
— including industry, government, academia, and nonprofit — to manage and reduce their
cybersecurity risks. It is useful regardless of the maturity level and technical sophistication of an
organization’s cybersecurity programs. Nevertheless, the CSF does not embrace a one-size-fits-
all approach. Each organization has both common and unique risks, as well as varying risk
appetites and tolerances, specific missions, and objectives to achieve those missions. By
necessity, the way organizations implement the CSF will vary.

Ideally, the CSF will be used to address cybersecurity risks alongside other risks of the
enterprise, including those that are financial, privacy, supply chain, reputational, technological,
or physical in nature.

The CSF describes desired outcomes that are intended to be understood by a broad audience,
including executives, managers, and practitioners, regardless of their cybersecurity expertise.
Because these outcomes are sector-, country-, and technology-neutral, they provide an
organization with the flexibility needed to address their unique risks, technologies, and mission
considerations. Outcomes are mapped directly to a list of potential security controls for
immediate consideration to mitigate cybersecurity risks.

Although not prescriptive, the CSF assists its users in learning about and selecting specific
outcomes. Suggestions for how specific outcomes may be achieved are provided in an
expanding suite of online resources that complement the CSF, including a series of Quick Start
Guides (QSGs). Also, various tools offer downloadable formats to help organizations that
choose to automate some of their processes. The QSGs suggest initial ways to use the CSF and
invite the reader to explore the CSF and related resources in greater depth. Available through
the NIST CSF website, the CSF and these supplementary resources from NIST and others should
be viewed as a “CSF portfolio” to help manage and reduce risks. Regardless of how it is applied,
the CSF prompts its users to consider their cybersecurity posture in context and then adapt the
CSF to their specific needs.

Building on previous versions, CSF 2.0 contains new features that highlight the importance of
governance and supply chains. Special attention is paid to the QSGs to ensure that the CSF is
relevant and readily accessible by smaller organizations as well as their larger counterparts.
NIST now provides Implementation Examples and Informative References, which are available
online and updated regularly. Creating current and target state Organizational Profiles helps
organizations to compare where they are versus where they want or need to be and allows
them to implement and assess security controls more quickly.

Cybersecurity risks are expanding constantly, and managing those risks must be a continuous
process. This is true regardless of whether an organization is just beginning to confront its
cybersecurity challenges or whether it has been active for many years with a sophisticated,
well-resourced cybersecurity team. The CSF is designed to be valuable for any type of
organization and is expected to provide appropriate guidance over a long time.

 iv

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

1. Cybersecurity Framework (CSF) Overview

This document is version 2.0 of the NIST Cybersecurity Framework (Framework or CSF). It
includes the following components:

•  CSF Core, the nucleus of the CSF, which is a taxonomy of high-level cybersecurity

outcomes that can help any organization manage its cybersecurity risks. The CSF Core
components are a hierarchy of Functions, Categories, and Subcategories that detail each
outcome. These outcomes can be understood by a broad audience, including
executives, managers, and practitioners, regardless of their cybersecurity expertise.
Because the outcomes are sector-, country-, and technology-neutral, they provide an
organization with the flexibility needed to address its unique risks, technologies, and
mission considerations.

•  CSF Organizational Profiles, which are a mechanism for describing an organization’s
current and/or target cybersecurity posture in terms of the CSF Core’s outcomes.

•  CSF Tiers, which can be applied to CSF Organizational Profiles to characterize the rigor of
an organization’s cybersecurity risk governance and management practices. Tiers can
also provide context for how an organization views cybersecurity risks and the processes
in place to manage those risks.

This document describes what desirable outcomes an organization can aspire to achieve. It
does not prescribe outcomes nor how they may be achieved. Descriptions of how an
organization can achieve those outcomes are provided in a suite of online resources that
complement the CSF and are available through the NIST CSF website. These resources offer
additional guidance on practices and controls that could be used to achieve outcomes and are
intended to help an organization understand, adopt, and use the CSF. They include:

•

•

Informative References that point to sources of guidance on each outcome from existing
global standards, guidelines, frameworks, regulations, policies, etc.

Implementation Examples that illustrate potential ways to achieve each outcome

•  Quick-Start Guides that give actionable guidance on using the CSF and its online
resources, including transitioning from previous CSF versions to version 2.0

•  Community Profiles and Organizational Profile Templates that help an organization put

the CSF into practice and set priorities for managing cybersecurity risks

An organization can use the CSF Core, Profiles, and Tiers with the supplementary resources to
understand, assess, prioritize, and communicate cybersecurity risks.

•  Understand and Assess: Describe the current or target cybersecurity posture of part or
all of an organization, determine gaps, and assess progress toward addressing those
gaps.

1

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

•  Prioritize: Identify, organize, and prioritize actions for managing cybersecurity risks that

align with the organization’s mission, legal and regulatory requirements, and risk
management and governance expectations.

•  Communicate: Provide a common language for communicating inside and outside the

organization about cybersecurity risks, capabilities, needs, and expectations.

The CSF is designed to be used by organizations of all sizes and sectors, including industry,
government, academia, and nonprofit organizations, regardless of the maturity level of their
cybersecurity programs. The CSF is a foundational resource that may be adopted voluntarily
and through governmental policies and mandates. The CSF’s taxonomy and referenced
standards, guidelines, and practices are not country-specific, and previous versions of the CSF
have been leveraged successfully by many governments and other organizations both inside
and outside of the United States.

The CSF should be used in conjunction with other resources (e.g., frameworks, standards,
guidelines, leading practices) to better manage cybersecurity risks and inform the overall
management of information and communications technology (ICT) risks at an enterprise level.
The CSF is a flexible framework that is intended to be tailored for use by all organizations
regardless of size. Organizations will continue to have unique risks — including different threats
and vulnerabilities — and risk tolerances, as well as unique mission objectives and
requirements. Thus, organizations’ approaches to managing risks and their implementations of
the CSF will vary.

The remainder of this document is structured as follows:

•  Section 2 explains the basics of the CSF Core: Functions, Categories, and Subcategories.

•  Section 3 defines the concepts of CSF Profiles and Tiers.

•  Section 4 provides an overview of selected components of the CSF’s suite of online

resources: Informative References, Implementation Examples, and Quick Start Guides.

•  Section 5 discusses how an organization can integrate the CSF with other risk

management programs.

•  Appendix A is the CSF Core.

•  Appendix B contains a notional illustration of the CSF Tiers.

•  Appendix C is a glossary of CSF terminology.

2

NIST CSWP 29
February 26, 2024

2. Introduction to the CSF Core

The NIST Cybersecurity Framework (CSF) 2.0

Appendix A is the CSF Core — a set of cybersecurity outcomes arranged by Function, then
Category, and finally Subcategory, as depicted in Fig. 1. These outcomes are not a checklist of
actions to perform; specific actions taken to achieve an outcome will vary by organization and
use case, as will the individual responsible for those actions. Additionally, the order and size of
Functions, Categories, and Subcategories in the Core does not imply the sequence or
importance of achieving them. The structure of the Core is intended to resonate most with
those charged with operationalizing risk management within an organization.

Fig. 1. CSF Core structure

The CSF Core Functions — GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, and RECOVER — organize
cybersecurity outcomes at their highest level.

•  GOVERN (GV) — The organization’s cybersecurity risk management strategy,

expectations, and policy are established, communicated, and monitored. The GOVERN
Function provides outcomes to inform what an organization may do to achieve and
prioritize the outcomes of the other five Functions in the context of its mission and
stakeholder expectations. Governance activities are critical for incorporating
cybersecurity into an organization’s broader enterprise risk management (ERM)
strategy. GOVERN addresses an understanding of organizational context; the
establishment of cybersecurity strategy and cybersecurity supply chain risk
management; roles, responsibilities, and authorities; policy; and the oversight of
cybersecurity strategy.

•

IDENTIFY (ID) — The organization’s current cybersecurity risks are understood.
Understanding the organization’s assets (e.g., data, hardware, software, systems,
facilities, services, people), suppliers, and related cybersecurity risks enables an
organization to prioritize its efforts consistent with its risk management strategy and the
mission needs identified under GOVERN. This Function also includes the identification of

3

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

improvement opportunities for the organization’s policies, plans, processes, procedures,
and practices that support cybersecurity risk management to inform efforts under all six
Functions.

•  PROTECT (PR) — Safeguards to manage the organization’s cybersecurity risks are used.
Once assets and risks are identified and prioritized, PROTECT supports the ability to
secure those assets to prevent or lower the likelihood and impact of adverse
cybersecurity events, as well as to increase the likelihood and impact of taking
advantage of opportunities. Outcomes covered by this Function include identity
management, authentication, and access control; awareness and training; data security;
platform security (i.e., securing the hardware, software, and services of physical and
virtual platforms); and the resilience of technology infrastructure.

•  DETECT (DE) — Possible cybersecurity attacks and compromises are found and analyzed.

DETECT enables the timely discovery and analysis of anomalies, indicators of
compromise, and other potentially adverse events that may indicate that cybersecurity
attacks and incidents are occurring. This Function supports successful incident response
and recovery activities.

•  RESPOND (RS) — Actions regarding a detected cybersecurity incident are taken. RESPOND
supports the ability to contain the effects of cybersecurity incidents. Outcomes within
this Function cover incident management, analysis, mitigation, reporting, and
communication.

•  RECOVER (RC) — Assets and operations affected by a cybersecurity incident are restored.
RECOVER supports the timely restoration of normal operations to reduce the effects of
cybersecurity incidents and enable appropriate communication during recovery efforts.

While many cybersecurity risk management activities focus on preventing negative events
from occurring, they may also support taking advantage of positive opportunities. Actions to
reduce cybersecurity risk might benefit an organization in other ways, like increasing
revenue (e.g., first offering excess facility space to a commercial hosting provider for hosting
their own and other organizations’ data centers, then moving a major financial system from
the organization’s in-house data center to the hosting provider to reduce cybersecurity
risks).

Figure 2 shows the CSF Functions as a wheel because all of the Functions relate to one another.
For example, an organization will categorize assets under IDENTIFY and take steps to secure
those assets under PROTECT. Investments in planning and testing in the GOVERN and IDENTIFY
Functions will support timely detection of unexpected events in the DETECT Function, as well as
enabling incident response and recovery actions for cybersecurity incidents in the RESPOND and
RECOVER Functions. GOVERN is in the center of the wheel because it informs how an organization
will implement the other five Functions.

4

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

Fig. 2. CSF Functions

The Functions should be addressed concurrently. Actions that support GOVERN, IDENTIFY, PROTECT,
and DETECT should all happen continuously, and actions that support RESPOND and RECOVER
should be ready at all times and happen when cybersecurity incidents occur. All Functions have
vital roles related to cybersecurity incidents. GOVERN, IDENTIFY, and PROTECT outcomes help
prevent and prepare for incidents, while GOVERN, DETECT, RESPOND, and RECOVER outcomes help
discover and manage incidents.

Each Function is named after a verb that summarizes its contents. Each Function is divided into
Categories, which are related cybersecurity outcomes that collectively comprise the Function.
Subcategories further divide each Category into more specific outcomes of technical and
management activities. The Subcategories are not exhaustive, but they describe detailed
outcomes that support each Category.

The Functions, Categories, and Subcategories apply to all ICT used by an organization, including
information technology (IT), the Internet of Things (IoT), and operational technology (OT). They
also apply to all types of technology environments, including cloud, mobile, and artificial
intelligence systems. The CSF Core is forward-looking and intended to apply to future changes
in technologies and environments.

5

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

3. Introduction to CSF Profiles and Tiers

This section defines the concepts of CSF Profiles and Tiers.

3.1. CSF Profiles

A CSF Organizational Profile describes an organization’s current and/or target cybersecurity
posture in terms of the Core’s outcomes. Organizational Profiles are used to understand, tailor,
assess, prioritize, and communicate the Core’s outcomes by considering an organization’s
mission objectives, stakeholder expectations, threat landscape, and requirements. An
organization can then prioritize its actions to achieve specific outcomes and communicate that
information to stakeholders.

Every Organizational Profile includes one or both of the following:

1.  A Current Profile specifies the Core outcomes that an organization is currently achieving
(or attempting to achieve) and characterizes how or to what extent each outcome is
being achieved.

2.  A Target Profile specifies the desired outcomes that an organization has selected and
prioritized for achieving its cybersecurity risk management objectives. A Target Profile
considers anticipated changes to the organization’s cybersecurity posture, such as new
requirements, new technology adoption, and threat intelligence trends.

A Community Profile is a baseline of CSF outcomes that is created and published to address
shared interests and goals among a number of organizations. A Community Profile is
typically developed for a particular sector, subsector, technology, threat type, or other use
case. An organization can use a Community Profile as the basis for its own Target Profile.
Examples of Community Profiles can be found on the NIST CSF website.

The steps shown in Fig. 3 and summarized below illustrate one way that an organization could
use an Organizational Profile to help inform continuous improvement of its cybersecurity.

Fig. 3. Steps for creating and using a CSF Organizational Profile

6

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

1.  Scope the Organizational Profile. Document the high-level facts and assumptions on
which the Profile will be based to define its scope. An organization can have as many
Organizational Profiles as desired, each with a different scope. For example, a Profile
could address an entire organization or be scoped to an organization’s financial systems
or to countering ransomware threats and handling ransomware incidents involving
those financial systems.

2.  Gather the information needed to prepare the Organizational Profile. Examples of
information may include organizational policies, risk management priorities and
resources, enterprise risk profiles, business impact analysis (BIA) registers, cybersecurity
requirements and standards followed by the organization, practices and tools (e.g.,
procedures and safeguards), and work roles.

3.  Create the Organizational Profile. Determine what types of information the Profile

should include for the selected CSF outcomes, and document the needed information.
Consider the risk implications of the Current Profile to inform Target Profile planning
and prioritization. Also, consider using a Community Profile as the basis for the Target
Profile.

4.  Analyze the gaps between the Current and Target Profiles, and create an action plan.
Conduct a gap analysis to identify and analyze the differences between the Current and
Target Profiles, and develop a prioritized action plan (e.g., risk register, risk detail report,
Plan of Action and Milestones [POA&M]) to address those gaps.

5.  Implement the action plan, and update the Organizational Profile. Follow the action

plan to address the gaps and move the organization toward the Target Profile. An action
plan may have an overall deadline or be ongoing.

Given the importance of continual improvement, an organization can repeat these steps as
often as needed.

There are additional uses for Organizational Profiles. For example, a Current Profile can be used
to document and communicate the organization’s cybersecurity capabilities and known
opportunities for improvement with external stakeholders, such as business partners or
prospective customers. Also, a Target Profile can help express the organization’s cybersecurity
risk management requirements and expectations to suppliers, partners, and other third parties
as a target for those parties to achieve.

3.2. CSF Tiers

An organization can choose to use the Tiers to inform its Current and Target Profiles. Tiers
characterize the rigor of an organization’s cybersecurity risk governance and management
practices, and they provide context for how an organization views cybersecurity risks and the
processes in place to manage those risks. The Tiers, as shown in Fig. 4 and notionally illustrated
in Appendix B, reflect an organization’s practices for managing cybersecurity risk as Partial (Tier
1), Risk Informed (Tier 2), Repeatable (Tier 3), and Adaptive (Tier 4). The Tiers describe a
progression from informal, ad hoc responses to approaches that are agile, risk-informed, and

7

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

continuously improving. Selecting Tiers helps set the overall tone for how an organization will
manage its cybersecurity risks.

Fig. 4. CSF Tiers for cybersecurity risk governance and management

Tiers should complement an organization’s cybersecurity risk management methodology rather
than replace it. For example, an organization can use the Tiers to communicate internally as a
benchmark for an organization-wide1
 approach to managing cybersecurity risks. Progression to
higher Tiers is encouraged when risks or mandates are greater or when a cost-benefit analysis
indicates a feasible and cost-effective reduction of negative cybersecurity risks.

The NIST CSF website provides additional information on using Profiles and Tiers. It includes
pointers to NIST-hosted Organizational Profile templates and a repository of Community
Profiles in a variety of machine-readable and human-usable formats.

1 For the purposes of this document, the terms “organization-wide” and “enterprise” have the same meaning.

8

NIST CSWP 29
February 26, 2024

The NIST Cybersecurity Framework (CSF) 2.0

4. Introduction to Online Resources That Supplement the CSF

NIST and other organizations have produced a suite of online resources that help organizations
understand, adopt, and use the CSF. Since they are hosted online, these additional resources
can be updated more frequently than this document, which is updated infrequently to provide
stability to its users, and be available in machine-readable formats. This section provides an
overview of three types of online resources: Informative References, Implementation Examples,
and Quick Start Guides.

Informative References are mappings that indicate relationships between the Core and various
standards, guidelines, regulations, and other content. Informative References help inform how
an organization may achieve the Core’s outcomes. Informative References can be sector- or
technology-specific. They may be produced by NIST or another organization. Some Informative
References are narrower in scope than a Subcategory. For example, a particular control from SP
800-53, Security and Privacy Controls for Information Systems and Organizations, may be one of
many references needed to achieve the outcome described in one Subcategory. Other
Informative References may be higher-level, such as a requirement from a policy that partially
addresses numerous Subcategories. When using the CSF, an organization can identify the most
relevant Informative References.

Implementation Examples provide notional examples of concise, action-oriented steps to help
achieve the outcomes of the Subcategories. Verbs used to express Examples include share,
document, develop, perform, monitor, analyze, assess, and exercise. The Examples are not a
comprehensive list of all actions that could be taken by an organization to achieve an outcome,
nor do they represent a baseline of required actions to address cybersecurity risks.

Quick-Start Guides (QSGs) are brief documents on specific CSF-related topics and are often
tailored to specific audiences. QSGs can help an organization implement the CSF because they
distill specific portions of the CSF into actionable “first steps” that an organization can consider
on the path to improving their cybersecurity posture and management of associated risks. The
guides are revised in their own time frames, and new guides are added as needed.

Suggestions for new Informative References for CSF 2.0 can always be shared with NIST at
olir@nist.gov. Suggestions for other resources to reference on the NIST CSF website, including
additional QSG topics, should be directed to cyberframework@nist.gov.

9

