# AWS account and credit deadline

Status: partially confirmed by user on 2026-10-25. No account-specific dates or credit amounts have been assumed.

## Required values

- AWS region: `ap-south-1` (user-provided).
- AWS plan/account type: user reports a six-month AWS Free Tier account; exact account plan classification remains unverified.
- Existing charges shown in Billing: pending user confirmation.
- Remaining credits and expiry date: pending confirmation in Billing > Free Tier.
- Account creation date: pending confirmation.
- Root-user MFA: pending confirmation.
- Zero-spend Budget alert: pending confirmation.
- Free Tier usage alerts: pending confirmation.
- Credit end date: pending.
- Backup date (two weeks before credit end date): pending.

## A0 safety checklist

- [ ] Confirm the account/plan classification, remaining credits and expiry, account creation date, and current charges in Billing > Free Tier / Credits.
- [ ] Record the expiry date above and set the backup date to 14 days earlier.
- [ ] Confirm root-user MFA is enabled. If not, enable it in the root security credentials page.
- [ ] Confirm the AWS Budgets zero-spend alert is configured. If not, create the $0 budget alert in Billing > Budgets.
- [ ] Confirm Free Tier usage alerts are enabled. If not, enable them in Billing > Billing preferences.

No AWS resources are created during Stage A.
