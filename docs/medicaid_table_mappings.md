# Medicaid Database Table Mappings

This document provides mappings between business entity names and their corresponding database table names for the Medicaid rebate processing system. These mappings help the SQL Agent understand the semantic meaning of database tables when analyzing queries.

## Core Claims Processing Tables

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdClaim | MN_MCD_CLAIM | Main claim information table storing basic claim data including claim status, numbers, dates |
| McdAdjustClaim | MN_MCD_CLAIM | Adjusted claims (same table as McdClaim with different type) |
| McdConvClaim | MN_MCD_CLAIM | Converted claims (same table as McdClaim with different type) |
| McdOrigClaim | MN_MCD_CLAIM | Original claims (same table as McdClaim with different type) |
| McdClaimLine | MN_MCD_CLAIM_LINE | Line items for claims, containing URA values, units, rebate amounts |
| McdAdjustClaimLine | MN_MCD_CLAIM_LINE | Adjusted claim line items (same table with different type) |
| McdConvClaimLine | MN_MCD_CLAIM_LINE | Converted claim line items (same table with different type) |
| McdSettlement | MN_MCD_SETTLEMENT | Settlement information for disputed or resolved units |

## Payment Processing Tables

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdPayment | MN_MCD_PAYMENT | Payment transaction information |
| McdClaimPmt | MN_MCD_CLAIM_PMT | Claim payment details linking claims to payments |
| McdClaimPmtInterest | MN_MCD_CLAIM_PMT_INTR | Interest calculation for late payments |
| McdExternalCredit | MN_MCD_EXTERNAL_CREDIT | External credit information |
| McdExternalCreditPmt | MN_MCD_EXTERNAL_CREDIT_PMT | External credit payment associations |
| McdPaymentReportStatus | MN_MCD_PAY_RPT_STUS | Payment report generation status |

## Program Configuration Tables

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdProgram | MN_MCD_PROGRAM | Program configuration and details |
| McdProgramLI | MN_MCD_PROGRAM_LI | Program line items with product associations |
| ProgramStateConfig | MN_MCD_PROG_CONFIG | State-specific program configurations |
| McdProgramQualification | MN_MCD_PROG_QUAL | Program qualification rules |
| McdStateSuppMediLink | MN_MCD_SS_MEDI_LINK | State supplement to Medicaid linkages |

## Price List and Reference Tables

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdReimbursementInfo | MN_MCD_REIMBURSE_INFO | Reimbursement configuration information |
| UraPublishedPriceList | MN_MCD_PRICELIST_PUBLISHED | Published URA price list information |
| McdTolerances | MN_MCD_TOLERANCES | Validation tolerance settings |

## Mass Update Processing

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdMassUpdate | MN_MCD_MASS_UPDATE | Mass update job information |
| McdMassUpdateProduct | MN_MCD_MU_PRODUCT | Products affected by mass updates |
| McdMassUpdateProgram | MN_MCD_MU_PROG | Programs affected by mass updates |
| McdMassUpdateProgramLi | MN_MCD_MU_PROGLI | Program line items affected by mass updates |
| McdMassUpdateValidationMsg | MN_MCD_MU_VALIDATION_MSG | Validation messages for mass updates |

## Support and Metadata Tables

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdComment | MN_MCD_COMMENT | Comments associated with various entities |
| McdColumnOrder | MN_MCD_COL_ORDER | UI column ordering preferences |
| McdValidationMsg | MN_MCD_VALIDATION_MSG | Validation messages for claims |
| McdIntermediateResult | MN_MCD_INT_RESULT | Intermediate calculation results |

## Reporting Views

| Business Entity | Database Table | Description |
|----------------|---------------|-------------|
| McdReportingClaim | MN_MCD_REP_CLAIM_VW | Reporting view for claims |
| McdReportingClaimLine | MN_MCD_REP_CLAIM_LINE_VW | Reporting view for claim lines |
| McdReportingClmPmt | MN_MCD_REP_CLMPMT_VW | Reporting view for claim payments |
| McdReportingPayment | MN_MCD_REP_PAYMENT_VW | Reporting view for payments |
| McdReportingProgram | MN_MCD_REP_PROGRAM_VW | Reporting view for programs |
| McdReportingProgramLI | MN_MCD_REP_PROGRAM_LI_VW | Reporting view for program line items |
| McdCreditSummary | MN_MCD_CREDIT_SUMMARY_VW | Credit summary view |
| McdCreditSummaryPmtDetail | MN_MCD_CREDIT_SMRY_PMT_VW | Credit summary payment details view |
| McdQuarterClaim | MN_MCD_QTR_CLAIM_VW | Quarterly claim summary view |

## Key Table Relationships

- **Claims Hierarchy**: MN_MCD_CLAIM (parent) → MN_MCD_CLAIM_LINE (child) → MN_MCD_VALIDATION_MSG (validation)
- **Payment Hierarchy**: MN_MCD_PAYMENT (parent) → MN_MCD_CLAIM_PMT (association) → MN_MCD_CLAIM (claim)
- **Program Hierarchy**: MN_MCD_PROGRAM (parent) → MN_MCD_PROGRAM_LI (products) → MN_MCD_CLAIM_LINE (utilized)
