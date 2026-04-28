# Form 8949 Code B & ESPP / RSU / NQSO Basis Adjustment

This reference covers the most common single cause of ESPP/ISO/RSU overpayment: failure to apply the Form 8949 Code B basis adjustment. It also covers the reverse problem: unreported qualifying-disposition ordinary income that the employer did not add to the W-2.

## The Core Problem

For any stock acquired through an employer equity plan (ESPP, ISO, NQSO, RSU), the **1099-B cost basis is always too low** by the amount of ordinary income that was already taxed as wages. Reg § 1.6045-1(d)(6)(ii) (effective for grants after Jan 1, 2014) **prohibits brokers from including the compensation component** in the reported basis. The taxpayer must adjust it on Form 8949 using Code B.

Without the adjustment, the taxpayer pays tax twice on the same dollars:
1. Once as W-2 wages (ordinary income rate)
2. Again as capital gains (LT or ST rate)

Typical overpayment: 15% of the basis adjustment amount for LT shares, 35%+ for ST shares.

## Form 8949 Entry

| Column | Value |
|---|---|
| (a) Description | Security name (e.g., "MICROSOFT CORP") |
| (b) Date acquired | Per 1099-B |
| (c) Date sold | Per 1099-B |
| (d) Proceeds | Per 1099-B Box 1d |
| (e) Cost basis | Per 1099-B Box 1e (the WRONG number — keep as reported) |
| **(f) Code** | **B** (or BX if combined with another code) |
| **(g) Adjustment** | **NEGATIVE number** = −(ordinary income already taxed) |
| (h) Gain/(loss) | = (d) − (e) + (g) |

**The adjustment is always negative.** It reduces the gain (or increases the loss) by the missing basis.

## Computing the Adjustment by Plan Type

### ESPP — Qualified Section 423 Plan

**Data needed:**
- Purchase price (what employee paid)
- FMV on purchase date
- FMV on grant date (offering period start)
- Sale price (FMV on sale date for this formula)
- Grant date, purchase date, sale date

**Holding period tests (BOTH must be met for qualifying):**
1. > 1 year after purchase date
2. > 2 years after grant date (offering period start)

### ESPP Qualifying Disposition

Ordinary income (already in or missing from W-2) = **lesser of:**
- (FMV at grant date − purchase price) × shares — the "original discount"
- (Sale price − purchase price) × shares — the actual gain

Capital gain = Sale proceeds − purchase price − ordinary income

**Basis adjustment (column g) = −(ordinary income)**

**Where to report ordinary income if NOT on W-2:** Schedule 1, Line 8k ("Stock options"). Most employers stopped adding qualifying-disposition ordinary income to W-2 after the 2009 IRS ruling that made it optional. The employee self-reports.

### ESPP Disqualifying Disposition

Ordinary income (always on W-2 — employers ARE required to add DQ disposition income) = (FMV on purchase date − purchase price) × shares — the full discount at purchase

Capital gain/(loss) = Sale proceeds − purchase price − ordinary income = Sale proceeds − FMV on purchase date

**Basis adjustment (column g) = −(ordinary income)**

### Qualifying vs Disqualifying — Key Differences

| Aspect | Qualifying | Disqualifying |
|---|---|---|
| Holding | > 2 yr grant AND > 1 yr purchase | Either test missed |
| Ordinary income | Lesser of grant discount or actual gain | Full discount at purchase |
| On W-2? | Often NOT (employer not required since 2009) | YES (employer required) |
| Self-report? | Schedule 1 Line 8k if not on W-2 | Never (already in W-2 Box 1) |
| Capital gain type | Long-term | Short-term if within 1 yr of purchase; long-term otherwise |

### RSU / Restricted Stock

Ordinary income was recognized at **vest date** = vest-date FMV × shares vested. Already in W-2 Box 1 of the vest-year W-2.

Basis for later sale should be vest-date FMV. But the 1099-B often shows $0 (or the original grant-date FMV, which is wrong).

**Basis adjustment = +(vest-date FMV × shares sold)** — i.e., a negative number in column (g) equal to what's missing.

### ISO (Incentive Stock Option)

Two tax paths depending on whether qualifying or disqualifying:

**Qualifying disposition (held >2yr from grant AND >1yr from exercise):**
- Exercise creates AMT adjustment (spread taxable under AMT only)
- Sale is long-term capital gain: proceeds − exercise price
- No Code B adjustment needed for regular tax
- For AMT basis: AMT basis = exercise price + AMT adjustment = FMV on exercise date

**Disqualifying disposition:**
- Ordinary income = FMV on exercise − exercise price (already in W-2 Box 1 for year of disposition)
- Capital gain/(loss) = proceeds − FMV on exercise date
- Basis adjustment needed = −(ordinary income)

### NQSO (Non-Qualified Stock Option)

Ordinary income at exercise = (FMV on exercise − exercise price) × shares. Always in W-2 Box 1 for the year of exercise.

1099-B basis = exercise price (what was paid). Correct basis = FMV on exercise date.

**Basis adjustment = −(ordinary income)** = −(FMV on exercise − exercise price) × shares

## Reading the Broker's "Supplemental Stock Plan" Section

Most major brokers (Fidelity, Schwab, E*TRADE/Morgan Stanley, Merrill) include a "Supplemental" or "Adjusted" section in the 1099 that shows the correct basis. These values are NOT reported to the IRS — they're informational — but they tell the taxpayer what the adjustment should be.

Look for:
- "Adjusted Cost or Other Basis"
- "Ordinary Income Reported" column
- "Supplemental Stock Plan Lot Detail"

For each lot, the adjustment = Reported basis − Adjusted basis = −(ordinary income reported)

Sum across all lots to get the total column (g) adjustment.

## The Lot-Level Reconciliation Trick

For ESPP, the "DQDIS" or equivalent amount in W-2 Box 14 represents ONLY the disqualifying disposition ordinary income for the year of sale. If the broker's supplemental shows MORE ordinary income than Box 14, the difference represents **qualifying disposition** ordinary income that is NOT on the W-2.

**Math check:**
```
Σ(ordinary income in broker supplemental) = W-2 Box 14 DQDIS
    + (qualifying disposition income NOT on W-2, self-reported on Schedule 1 Line 8k)
```

Walk through each lot's dates to identify which are DQ and which are Q:
- DQ (holding period failed) → already in W-2, just adjust basis
- Q (both holding periods met) → NOT in W-2, adjust basis AND report on Schedule 1 Line 8k

When the math reconciles exactly to Box 14, your lot classification is correct.

## FreeTaxUSA / Tax Software Workflow

Most major tax software handles the ESPP adjustment via a checkbox during 1099-B entry:

1. Enter the 1099-B as reported
2. Check "This is employer stock from ESPP/ISO/RSU"
3. Software asks "Did the broker report correct basis including the compensation component?"
4. Answer NO
5. Enter the adjusted basis (from the supplemental)
6. Software auto-generates Form 8949 with Code B

For the qualifying disposition self-reporting (Schedule 1 Line 8k), search the software for "Stock options" or "Other earned income" and enter the amount with a description like "ESPP qualifying disposition ordinary income."

## Red Flags During Review

When reviewing an ESPP taxpayer's return, check:

1. **Is Form 8949 missing Code B entirely?** The 1099-B basis almost certainly needs adjustment. Ask for the broker supplemental.
2. **Does the supplemental "Ordinary Income Reported" match W-2 Box 14 DQDIS?** If supplemental > Box 14, the gap is qualifying-disposition income that needs Schedule 1 Line 8k reporting.
3. **Are all lots post-2013 grants?** Pre-2014 grants may have basis already adjusted by the broker (different rules). Post-2014 always need Code B.
4. **Did the taxpayer ever have an ESPP payroll deduction?** If yes, at least some compensation component exists.
5. **Were any shares RSU vestings?** Vest-date basis adjustment is a separate category from ESPP discount — don't conflate them.

## Sources

- Instructions for Form 8949 (2025): https://www.irs.gov/instructions/i8949
- IRS Pub 525 (2025): https://www.irs.gov/publications/p525
- IRS FAQ Stocks/Options 5: https://www.irs.gov/faqs/capital-gains-losses-and-sale-of-home/stocks-options-splits-traders/stocks-options-splits-traders-5
- IRS Topic 427 (Stock Options): https://www.irs.gov/taxtopics/tc427
- Reg § 1.6045-1(d)(6)(ii) — basis reporting restriction
- IRC § 421, 422, 423 (statutory stock options and ESPPs)
- IRS Notice 2002-47 (FICA/withholding exemption for ESPP/ISO ordinary income)
