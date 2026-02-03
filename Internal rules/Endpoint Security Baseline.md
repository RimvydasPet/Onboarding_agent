---
doc_id: IT-002
title: Endpoint Security Baseline
department: IT Security
confidentiality: Internal
version: 1.0
effective_date: 2026-01-15
owner_role: Security Officer
review_cycle: 6 months
tags: [baseline, hardening, encryption, patching, mdm, edr]
---

# Endpoint Security Baseline

## Purpose
Establish a minimum security standard for laptops and desktops to reduce risk from malware, phishing, and data loss.

## Scope
All company-managed endpoints, including loaner devices and developer workstations.

## Baseline requirements
### Identity and access
- MFA is required for all corporate accounts.
- Local admin rights are restricted; requests must be justified and time-bound.

### Device protection
- Full-disk encryption must be enabled.
- Endpoint detection and response (EDR) must be installed and active.
- Host firewall must be enabled.

### Updates and patching
- OS security updates must install within 7 days of release for critical patches.
- Browser updates must be installed within 7 days.
- Unsupported OS versions are not permitted.

### Configuration
- Screen lock after 10 minutes of inactivity.
- Password manager usage is required for storing credentials.
- USB storage is restricted for Confidential data.

## Developer-specific allowances
Developer tools may require broader permissions, but must follow:
- Separate dev environments when possible.
- No production secrets stored unencrypted on endpoints.
- Secure key handling (hardware-backed where available).

## Compliance checks
IT Security performs periodic compliance checks via management tools. Non-compliant devices may be quarantined from corporate services until remediated.

## Exceptions
Exceptions must document: justification, risk, compensating controls, owner, and expiry.
