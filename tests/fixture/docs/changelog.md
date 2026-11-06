# Changelog

All notable changes to the fixture application are recorded here. The format is
loosely based on Keep a Changelog, and versions follow semantic versioning.

## [Unreleased]

### Added

- Notes about a future JSON report format.

### Changed

- Nothing yet.

### Fixed

- Nothing yet.

## [1.4.0] - 2026-09-18

### Added

- `validate` CLI command that reports malformed invoice lines.
- `invoice_rows` helper shared by the summary and report commands.
- Unit tests for discount validation.

### Changed

- `main.py` now maps handled errors to a single friendly message instead of a
  traceback.
- The README documents every supported command.

### Fixed

- CSV export no longer leaves a trailing blank line on Windows.

## [1.3.2] - 2026-08-27

### Added

- `sort_by_issued` helper for stable report ordering.

### Changed

- Monthly reports list the oldest invoice first.

### Fixed

- Customer totals no longer include invoices from adjacent months.

## [1.3.1] - 2026-08-11

### Added

- Tests for `apply_discount` bounds.

### Changed

- Discount percentages are validated before any line is copied.

### Fixed

- Applying a discount twice no longer compounds silently in caller code
  because the input list is left untouched.

## [1.3.0] - 2026-07-30

### Added

- Per invoice `tax_rate` overrides.
- Document level default tax rate.

### Changed

- The loader accepts both a bare list and an object with an `invoices` key.

### Fixed

- A missing `issued` field now raises a clear error instead of a `KeyError`.

## [1.2.4] - 2026-07-09

### Added

- `customer_totals` report helper.

### Changed

- Customer names are normalised before grouping.
- Report totals are sorted from largest to smallest.

### Fixed

- Customers whose names differ only in casing are grouped together.

## [1.2.3] - 2026-06-22

### Added

- Text table renderer with configurable columns.

### Changed

- The report footer now includes the invoice count.

### Fixed

- Very long customer names are truncated rather than pushing the table width
  out indefinitely.

## [1.2.2] - 2026-06-05

### Added

- `month_bounds` and `in_month` helpers.

### Changed

- Date parsing is centralised in `utils.parse_date`.

### Fixed

- December reports no longer include January invoices.

## [1.2.1] - 2026-05-19

### Added

- CSV export command.

### Changed

- `CSV_COLUMNS` is a module constant so downstream consumers can rely on the
  header order.

### Fixed

- Exported amounts always use two decimal places.

## [1.2.0] - 2026-05-02

### Added

- Monthly report command.
- Summary command with subtotal, tax and total.

### Changed

- Argument parsing moved into `build_parser` for easier testing.

### Fixed

- Help text is printed when no subcommand is supplied.

## [1.1.3] - 2026-04-14

### Added

- Utility helpers for padding and truncation.

### Changed

- The report table uses `utils.pad` everywhere.

### Fixed

- Multibyte characters no longer break column alignment.

## [1.1.2] - 2026-04-01

### Added

- Tests for the invoice line validation rules.

### Changed

- Zero quantities are rejected rather than treated as free items.

### Fixed

- Negative unit prices produce a validation error instead of reducing the
  invoice total.

## [1.1.1] - 2026-03-20

### Added

- `group_by` and `chunked` sequence helpers.

### Changed

- JSON output is written with sorted keys.

### Fixed

- Writing a report to a new directory now creates the directory first.

## [1.1.0] - 2026-03-07

### Added

- Discount support through `apply_discount`.
- Maximum discount constant.

### Changed

- Discounted unit prices are fixed at the line level before tax is applied.

### Fixed

- A discount above one hundred percent is rejected.

## [1.0.0] - 2026-02-23

### Added

- First stable release of the invoicing fixture.
- Billing, reporting, utility and CLI modules.
- JSON loader and writer helpers.

### Changed

- Module boundaries were frozen for the first stable release.

### Fixed

- A missing input file produces exit code one.

## [0.9.0] - 2026-02-09

### Added

- Report footer with subtotal, tax and total.
- Money formatting helper.

### Changed

- All printed amounts go through the money helper.

### Fixed

- Amounts are no longer printed with four decimal places.

## [0.8.2] - 2026-01-26

### Added

- Second batch of date helpers.

### Changed

- Month names come from a single constant list.

### Fixed

- An invalid month number raises a validation error.

## [0.8.1] - 2026-01-12

### Added

- Initial date helpers.

### Changed

- Dates are parsed as ISO strings only.

### Fixed

- Trailing whitespace in dates is ignored.

## [0.8.0] - 2025-12-15

### Added

- CSV row builder.
- Column constants for exports.

### Changed

- Report rows use string amounts so that formatting happens once.

### Fixed

- Empty customer names are rejected before grouping.

## [0.7.0] - 2025-11-28

### Added

- Customer grouping in reports.

### Changed

- Grouping preserves the first display name it sees.

### Fixed

- Duplicate customers no longer appear twice in the table.

## [0.6.0] - 2025-11-10

### Added

- Utility module with money formatting.
- Percent formatting helper.

### Changed

- Formatting helpers live in `utils` instead of `billing`.

### Fixed

- Dashboard percentage labels no longer show a stray decimal after rounding.

## [0.5.0] - 2025-10-23

### Added

- Discount and validation tests.

### Changed

- Validation errors now name the offending line index.

### Fixed

- Validation accepts an empty list only when explicitly allowed.

## [0.4.0] - 2025-10-06

### Added

- Invoice summary row builder.

### Changed

- Subtotal calculation moved behind `subtotal_for`.

### Fixed

- Empty invoices return zero instead of raising.

## [0.3.0] - 2025-09-19

### Added

- Tax rate constant.
- Default rate wiring in the CLI.

### Changed

- The default rate is read from one place.

### Fixed

- A per invoice rate overrides the default consistently.

## [0.2.0] - 2025-09-01

### Added

- First version of the report table.
- Basic filtering by month.

### Changed

- Tables are rendered as plain text.

### Fixed

- Empty reports print a placeholder instead of a bare header.

## [0.1.0] - 2025-08-18

### Added

- Initial invoice line and total helpers.
- Command line skeleton.
- README and architecture notes.

### Changed

- Nothing yet.

### Fixed

- Nothing yet.

## Project conventions

- Every user visible change gets an entry.
- Fixed entries describe the symptom, not the implementation.
- Entries are written in the past tense.
- Version numbers are bumped before a release branch is cut.
- Dates are the release date, not the merge date.

## Ownership

The fixture is maintained by the platform team. Changes to the report format
should be reviewed by whoever owns the downstream spreadsheet import, because
column order is a contract. Changes to the arithmetic should be reviewed by the
billing team even though the module is small.
