# SOC 2 Requirements for Software Systems

> **Document Version**: 2025 (Based on AICPA 2017 Trust Services Criteria with 2022 Revised Points of Focus)
> **Downloaded**: 2026-01-21
> **Purpose**: Reference document for making Trinity compliant with SOC 2 Type II

---

## Overview

SOC 2 (System and Organization Controls 2) is a compliance framework developed by the American Institute of Certified Public Accountants (AICPA). It's designed for service organizations that store, process, or transmit customer data.

### Key Facts

- **Framework**: Based on COSO (Committee of Sponsoring Organizations) Internal Control Framework
- **Total Criteria**: 64 individual criteria across 5 Trust Services Categories
- **Required Criteria**: Only Security (Common Criteria) is mandatory
- **Report Types**:
  - **Type I**: Point-in-time assessment of control design
  - **Type II**: Assessment of control effectiveness over 3-12 months (more rigorous)

### Official Resources

- [AICPA SOC 2 Official Page](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2)
- 2017 Trust Services Criteria (Revised Points of Focus – 2022) - AICPA document
- 2018 SOC 2 Description Criteria (Revised Implementation Guidance – 2022)

---

## The Five Trust Services Criteria (TSC)

| Category | Code | Required | Description |
|----------|------|----------|-------------|
| **Security** | CC1-CC9 | **Yes** | Protecting information and systems against unauthorized access |
| **Availability** | A1 | No | Ensuring systems are available for operation |
| **Processing Integrity** | PI1 | No | Ensuring system processing is complete, accurate, timely |
| **Confidentiality** | C1 | No | Protecting confidential information |
| **Privacy** | P1-P8 | No | Safeguarding personal information (PII) |

---

## SECURITY: Common Criteria (CC1-CC9)

The Security category is the foundation of SOC 2 and includes 9 Common Criteria categories containing most of the 64 total criteria.

### CC1: Control Environment
**COSO Alignment**: Principles 1-5
**Focus**: Governance, ethics, organizational structure, accountability

| Criteria | Description | COSO Principle |
|----------|-------------|----------------|
| **CC1.1** | The entity demonstrates a commitment to integrity and ethical values | Principle 1 |
| **CC1.2** | The board of directors demonstrates independence from management and exercises oversight of the development and performance of internal control | Principle 2 |
| **CC1.3** | Management establishes, with board oversight, structures, reporting lines, and appropriate authorities and responsibilities in the pursuit of objectives | Principle 3 |
| **CC1.4** | The entity demonstrates a commitment to attract, develop, and retain competent individuals in alignment with objectives | Principle 4 |
| **CC1.5** | The entity holds individuals accountable for their internal control responsibilities in the pursuit of objectives | Principle 5 |

**Implementation Requirements**:
- Documented Code of Conduct / Employee Handbook (reviewed annually)
- Clear organizational structure with defined reporting lines
- Background checks for employees and contractors
- Security awareness training program
- Defined roles and responsibilities for security

---

### CC2: Communication and Information
**COSO Alignment**: Principles 13-15
**Focus**: Information flow, policy communication, stakeholder awareness

| Criteria | Description | COSO Principle |
|----------|-------------|----------------|
| **CC2.1** | The entity obtains or generates and uses relevant, quality information to support the functioning of internal control | Principle 13 |
| **CC2.2** | The entity internally communicates information, including objectives and responsibilities for internal control, necessary to support the functioning of internal control | Principle 14 |
| **CC2.3** | The entity communicates with external parties regarding matters affecting the functioning of internal control | Principle 15 |

**Implementation Requirements**:
- Security policies documented and accessible to all staff
- Regular communication of policy updates
- External communication procedures (customers, vendors, regulators)
- System description documentation

---

### CC3: Risk Assessment
**COSO Alignment**: Principles 6-9
**Focus**: Risk identification, analysis, and management

| Criteria | Description | COSO Principle |
|----------|-------------|----------------|
| **CC3.1** | The entity specifies objectives with sufficient clarity to enable the identification and assessment of risks relating to objectives | Principle 6 |
| **CC3.2** | The entity identifies risks to the achievement of its objectives across the entity and analyzes risks as a basis for determining how the risks should be managed | Principle 7 |
| **CC3.3** | The entity considers the potential for fraud in assessing risks to the achievement of objectives | Principle 8 |
| **CC3.4** | The entity identifies and assesses changes that could significantly impact the system of internal control | Principle 9 |

**Implementation Requirements**:
- Formal risk assessment process (at least annual)
- Risk register with identified threats and vulnerabilities
- Risk scoring methodology (likelihood x impact)
- Fraud risk assessment
- Change impact analysis procedures

---

### CC4: Monitoring Activities
**COSO Alignment**: Principles 16-17
**Focus**: Continuous monitoring, evaluation, and remediation

| Criteria | Description | COSO Principle |
|----------|-------------|----------------|
| **CC4.1** | The entity selects, develops, and performs ongoing and/or separate evaluations to ascertain whether the components of internal control are present and functioning | Principle 16 |
| **CC4.2** | The entity evaluates and communicates internal control deficiencies in a timely manner to those parties responsible for taking corrective action | Principle 17 |

**Implementation Requirements**:
- Automated monitoring tools (SIEM, log aggregation)
- Regular control testing
- Deficiency tracking and remediation
- Management review of control effectiveness
- Internal audit function (or equivalent)

---

### CC5: Control Activities
**COSO Alignment**: Principles 10-12
**Focus**: Policies, procedures, and control implementation

| Criteria | Description | COSO Principle |
|----------|-------------|----------------|
| **CC5.1** | The entity selects and develops control activities that contribute to the mitigation of risks to the achievement of objectives to acceptable levels | Principle 10 |
| **CC5.2** | The entity also selects and develops general control activities over technology to support the achievement of objectives | Principle 11 |
| **CC5.3** | The entity deploys control activities through policies that establish what is expected and procedures that put policies into action | Principle 12 |

**Implementation Requirements**:
- Documented security policies
- Implemented technical controls
- Preventive and detective controls
- Control testing procedures
- Policy acknowledgment by employees

---

### CC6: Logical and Physical Access Controls
**Focus**: Authentication, authorization, encryption, physical security

| Criteria | Description |
|----------|-------------|
| **CC6.1** | The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet the entity's objectives |
| **CC6.2** | Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users whose access is administered by the entity |
| **CC6.3** | The entity authorizes, modifies, or removes access to data, software, functions, and other protected information assets based on roles, responsibilities, or the system design and changes |
| **CC6.4** | The entity restricts physical access to facilities and protected information assets (for example, data center facilities, backup media storage, and other sensitive locations) to authorized personnel to meet the entity's objectives |
| **CC6.5** | The entity discontinues logical and physical protections over physical assets only after the ability to read or recover data and software from those assets has been diminished |
| **CC6.6** | The entity implements logical access security measures to protect against threats from sources outside its system boundaries |
| **CC6.7** | The entity restricts the transmission, movement, and removal of information to authorized internal and external users and processes, and protects it during transmission, movement, or removal to meet the entity's objectives |
| **CC6.8** | The entity implements controls to prevent or detect and act upon the introduction of unauthorized or malicious software to meet the entity's objectives |

**Implementation Requirements**:
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)
- Password policies (complexity, rotation)
- User provisioning/deprovisioning procedures
- Access reviews (quarterly recommended)
- Encryption at rest and in transit
- Network segmentation
- Firewall and intrusion detection
- Endpoint protection / anti-malware
- Physical security controls (badge access, cameras)
- Secure media disposal

---

### CC7: System Operations
**Focus**: Monitoring, incident detection, response, and recovery

| Criteria | Description |
|----------|-------------|
| **CC7.1** | To meet its objectives, the entity uses detection and monitoring procedures to identify (1) changes to configurations that result in the introduction of new vulnerabilities, and (2) susceptibilities to newly discovered vulnerabilities |
| **CC7.2** | The entity monitors system components and the operation of those components for anomalies that are indicative of malicious acts, natural disasters, and errors affecting the entity's ability to meet its objectives; anomalies are analyzed to determine whether they represent security events |
| **CC7.3** | The entity evaluates security events to determine whether they could or have resulted in a failure of the entity to meet its objectives (security incidents) and, if so, takes actions to prevent or address such failures |
| **CC7.4** | The entity responds to identified security incidents by executing a defined incident response program to understand, contain, remediate, and communicate security incidents, as appropriate |
| **CC7.5** | The entity identifies, develops, and implements activities to recover from identified security incidents |

**Implementation Requirements**:
- Vulnerability management program
- Penetration testing (annual recommended)
- Security monitoring (SIEM)
- Log aggregation and analysis
- Incident response plan
- Incident response team/roles
- Communication procedures
- Post-incident review process
- Disaster recovery planning
- Business continuity planning

---

### CC8: Change Management
**Focus**: SDLC, change control, testing, deployment

| Criteria | Description |
|----------|-------------|
| **CC8.1** | The entity authorizes, designs, develops or acquires, configures, documents, tests, approves, and implements changes to infrastructure, data, software, and procedures to meet its objectives |

**CC8.1 Points of Focus for Software Development**:

1. **Planning & Authorization**
   - Implement processes permitting system changes before development begins
   - Design and develop changes through structured planning
   - Authorize modifications prior to application

2. **Documentation & Tracking**
   - Document all system changes to support maintenance and user responsibilities
   - Track system changes before they're deployed

3. **Testing & Configuration**
   - Test system changes before application
   - Configure software using appropriate parameters to manage functionality

4. **Approval & Deployment**
   - Authorize changes before implementation
   - Deploy changes through formal processes

5. **Risk & Impact Assessment**
   - Identify and evaluate objectives impacted by system modifications
   - Assess whether modified systems meet organizational objectives throughout development

6. **Incident-Related Changes**
   - Detect infrastructure, data, software, and procedure changes needed to resolve incidents
   - Initiate change processes upon incident detection

7. **Baseline Management**
   - Create and preserve standard IT and control system configurations

8. **Emergency Provisions**
   - Establish expedited authorization, design, testing, and approval processes for time-critical changes

9. **Security & Privacy**
   - Safeguard confidential information during design, development, testing, and deployment phases
   - Protect personal information throughout SDLC processes

**Implementation Requirements for Software Organizations**:
- Documented Software Development Lifecycle (SDLC)
- Version control system (Git)
- Code review requirements (pull requests)
- Issue/ticket tracking system (Jira, GitHub Issues)
- Segregation of duties (developers cannot deploy to production directly)
- Testing requirements (unit, integration, security)
- Staging/QA environments
- Deployment approval process
- Rollback procedures
- Change documentation/changelog
- Configuration management
- Infrastructure as Code (IaC) practices

---

### CC9: Risk Mitigation
**Focus**: Business continuity, vendor management

| Criteria | Description |
|----------|-------------|
| **CC9.1** | The entity identifies, selects, and develops risk mitigation activities for risks arising from potential business disruptions |
| **CC9.2** | The entity assesses and manages risks associated with vendors and business partners |

**Implementation Requirements**:
- Business impact analysis
- Business continuity plan
- Disaster recovery plan
- Recovery time objectives (RTO) / Recovery point objectives (RPO)
- Vendor risk management program
- Third-party security assessments
- Vendor contracts with security requirements
- Critical vendor identification
- Vendor access controls

---

## AVAILABILITY CRITERIA (A1)

For organizations where system uptime is critical.

| Criteria | Description |
|----------|-------------|
| **A1.1** | The entity maintains, monitors, and evaluates current processing capacity and use of system components (infrastructure, data, and software) to manage capacity demand and to enable the implementation of additional capacity to help meet its objectives |
| **A1.2** | The entity authorizes, designs, develops or acquires, implements, operates, approves, maintains, and monitors environmental protections, software, data backup processes, and recovery infrastructure to meet its objectives |
| **A1.3** | The entity tests recovery plan procedures supporting system recovery to meet its objectives |

**Implementation Requirements**:
- Capacity monitoring and planning
- Infrastructure scaling procedures
- Data backup procedures
- Backup testing (regular restoration tests)
- Recovery procedures
- Uptime monitoring
- SLA definitions
- Redundancy and failover systems
- Geographic distribution (if applicable)

---

## PROCESSING INTEGRITY CRITERIA (PI1)

For organizations processing transactions or data where accuracy is critical.

| Criteria | Description |
|----------|-------------|
| **PI1.1** | The entity obtains or generates, uses, and communicates relevant, quality information regarding the objectives related to processing, including definitions of data processed and product and service specifications |
| **PI1.2** | The entity implements policies and procedures over system inputs, including controls over completeness and accuracy |
| **PI1.3** | The entity implements policies and procedures over system processing to result in products, services, and reporting to meet the entity's objectives |
| **PI1.4** | The entity implements policies and procedures to make available or deliver output completely, accurately, and timely |
| **PI1.5** | The entity implements policies and procedures to store inputs, items in processing, and outputs completely, accurately, and timely |

**Implementation Requirements**:
- Input validation
- Data quality checks
- Processing logs and audit trails
- Output verification
- Error handling and logging
- Data integrity checks (checksums, hashes)
- Transaction logging

---

## CONFIDENTIALITY CRITERIA (C1)

For organizations handling confidential information (trade secrets, IP, client data).

| Criteria | Description |
|----------|-------------|
| **C1.1** | The entity identifies and maintains confidential information to meet the entity's objectives related to confidentiality |
| **C1.2** | The entity disposes of confidential information to meet the entity's objectives related to confidentiality |

**Implementation Requirements**:
- Data classification policy
- Confidential data identification
- Access restrictions for confidential data
- Encryption of confidential data
- Secure disposal procedures
- Data retention policy
- DLP (Data Loss Prevention) tools

---

## PRIVACY CRITERIA (P1-P8)

For organizations collecting, processing, or storing Personally Identifiable Information (PII).

| Criteria | Focus Area |
|----------|------------|
| **P1** | Notice and Communication - Informing individuals about privacy policies |
| **P2** | Choice and Consent - Obtaining consent for data collection/use |
| **P3** | Collection - Limiting collection to what is necessary |
| **P4** | Use, Retention, and Disposal - Appropriate data lifecycle management |
| **P5** | Access - Individual access to their data and correction capabilities |
| **P6** | Disclosure and Notification - Third-party sharing controls |
| **P7** | Quality - Data accuracy, completeness, and relevance |
| **P8** | Monitoring and Enforcement - Compliance monitoring and violation handling |

**Implementation Requirements**:
- Privacy policy
- Consent mechanisms
- Data minimization practices
- Data subject access request (DSAR) procedures
- Data retention schedules
- Third-party data sharing agreements
- Privacy impact assessments
- Breach notification procedures

---

## SOC 2 for Software Development Organizations

### Recommended TSC Selection for SaaS/Software Companies

| Criteria | Recommendation | Rationale |
|----------|----------------|-----------|
| Security (CC1-CC9) | **Required** | Always included |
| Availability (A1) | **Recommended** | Most SaaS customers expect uptime guarantees |
| Processing Integrity (PI1) | Consider | If processing transactions or critical data |
| Confidentiality (C1) | **Recommended** | If handling customer business data |
| Privacy (P1-P8) | Consider | If handling PII |

### Key Software Development Controls

#### Version Control & Code Management
- All code in version control (Git)
- Branch protection rules
- Signed commits (optional but recommended)

#### Code Review
- Mandatory pull request reviews
- Minimum reviewer requirements
- Automated code analysis (linting, SAST)

#### Testing
- Unit tests
- Integration tests
- Security testing (SAST/DAST)
- Penetration testing (annual)

#### CI/CD Pipeline
- Automated builds
- Automated testing
- Security scanning in pipeline
- Deployment approvals
- Audit trail of deployments

#### Environment Management
- Separate development, staging, production environments
- Production access restricted
- Infrastructure as Code
- Configuration management

#### Secrets Management
- No secrets in code
- Secrets management system
- Regular rotation of credentials

#### Monitoring & Logging
- Application logging
- Security logging
- Log retention (typically 1 year for SOC 2)
- Alerting on anomalies

---

## Implementation Roadmap for Trinity

### Phase 1: Foundation (Policies & Documentation)
- [ ] Information Security Policy
- [ ] Acceptable Use Policy
- [ ] Access Control Policy
- [ ] Change Management Policy
- [ ] Incident Response Plan
- [ ] Business Continuity Plan
- [ ] Vendor Management Policy
- [ ] Data Classification Policy

### Phase 2: Technical Controls
- [ ] Access control implementation (RBAC)
- [ ] MFA enforcement
- [ ] Encryption (at rest and in transit)
- [ ] Logging and monitoring (Vector already in place)
- [ ] Vulnerability scanning
- [ ] Penetration testing

### Phase 3: Process Implementation
- [ ] Risk assessment process
- [ ] Vendor due diligence process
- [ ] Incident response procedures
- [ ] Change management process
- [ ] Access review process

### Phase 4: Evidence Collection & Monitoring
- [ ] Control evidence documentation
- [ ] Continuous monitoring setup
- [ ] Regular control testing
- [ ] Management review process

### Phase 5: Audit Preparation
- [ ] Gap assessment
- [ ] Remediation of gaps
- [ ] Pre-audit readiness assessment
- [ ] SOC 2 Type I audit
- [ ] SOC 2 Type II audit (6-12 months later)

---

## Trinity's Existing Compliance Alignment

Based on the current architecture, Trinity already has several SOC 2-aligned features:

| Control Area | Trinity Feature | SOC 2 Mapping |
|--------------|-----------------|---------------|
| Audit Logging | Vector log aggregation, `agent_activities` table | CC4, CC7 |
| Access Control | Email auth, JWT tokens, agent permissions | CC6 |
| Change Management | Git integration, changelog, version control | CC8 |
| Monitoring | WebSocket status updates, container telemetry | CC7 |
| Incident Response | Execution termination, emergency stop | CC7.4 |
| Data Protection | Redis credential encryption, container isolation | CC6.7 |
| Availability | Container health checks, restart policies | A1 |

### Gaps to Address

1. **Formal Policies**: Need documented security policies
2. **Risk Assessment**: No formal risk assessment process
3. **Vendor Management**: No formal vendor assessment process
4. **Penetration Testing**: Not yet performed
5. **Access Reviews**: No periodic access review process
6. **Business Continuity**: No formal BCP/DR documentation
7. **Audit Trail**: SEC-001 (comprehensive audit logging) pending implementation

---

## Sources

- [AICPA SOC 2 Official Page](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2)
- [Secureframe - Trust Services Criteria](https://secureframe.com/hub/soc-2/trust-services-criteria)
- [Secureframe - Common Criteria](https://secureframe.com/hub/soc-2/common-criteria)
- [Cherry Bekaert - SOC 2 TSC Guide](https://www.cbh.com/insights/articles/soc-2-trust-services-criteria-guide/)
- [Linford & Co - Trust Services Criteria](https://linfordco.com/blog/trust-services-critieria-principles-soc-2/)
- [Bright Defense - SOC 2 Controls List](https://www.brightdefense.com/resources/soc-2-controls-list/)
- [ISMS.online - CC1.1 Explained](https://www.isms.online/soc-2/controls/control-environment-cc1-1-explained/)
- [Hicomply - CC8 Change Management](https://www.hicomply.com/hub/soc-2-controls-cc8-change-management)
- [WorkOS - Developer's Guide to SOC 2](https://workos.com/guide/the-developers-guide-to-soc-2-compliance)
- [Scytale - Software Development SOC 2](https://scytale.ai/center/soc-2/how-to-ensure-your-software-development-complies-with-soc-2/)
- [Qodo - Change Management Automation](https://www.qodo.ai/blog/soc-2-compliance-for-busy-devs-change-management-automation-with-qodo/)
- [TrustCloud - Getting Started with SOC 2](https://community.trustcloud.ai/docs/grc-launchpad/grc-101/compliance/getting-started-with-soc-2-trust-service-criteria-selection-guide/)

---

## Next Steps

1. Review this document with stakeholders
2. Prioritize which Trust Services Criteria to pursue (recommend: Security + Availability + Confidentiality)
3. Conduct gap assessment against current state
4. Create implementation plan with timeline
5. Engage SOC 2 auditor for guidance
