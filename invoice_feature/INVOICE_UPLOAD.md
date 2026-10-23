# Invoice PDF upload

Restart the backend and frontend after installing dependencies (`npm install` in the backend). On Master or Merge, select **Upload Invoice PDF**, choose a searchable PDF, and select **Extract invoice**. Review/edit the extracted fields and click **Review import**, then **Save to Master + Merge**.

The parser supports the supplied RBC0006-style multi-page invoice layout. It reconstructs wrapped amounts using PDF text positions and checks line amounts and printed invoice totals before returning data. Scanned, encrypted or differently structured invoices are rejected with a visible message rather than guessed records. No OCR or external AI service is used. The original PDF is processed in memory and is not saved to the Documents archive.

`POST /api/invoices/extract` accepts multipart field `invoice` (PDF, at most 10 MB / 20 pages) and returns `{success, data: {filename, master: [...], merge: [...], warnings: [...]}}`. Saving uses the existing `POST /api/shipment-records/import/preview` and `POST /api/shipment-records/import` endpoints for each sheet. Records remain available in the existing shipment-list API and both views.

Master receives seller company, portal, warehouse code, PO number/date, destination, invoice number/date, total quantity, box count and tax/invoice totals. Merge receives ASIN, EAN, seller SKU, name, HSN, quantity, rate, taxable cost and IGST/total per line. No stock quantities, logistics dates or shipping status are inferred. Extra invoice destination PIN and E-Way Bill fields are preserved by the API.

Portal aliases `B2B_COCOBLU`, `COCOBLU RETAIL LIMITED`, `Cocoblu`, `CB` and `Cocoblu (CB)` resolve to the same existing company-scoped portal. Bill To is used when Portal is absent. Companies must already exist, using existing company matching rules.

Permissions are unchanged: Visitor read-only, Executive append-only imports; existing admin import/update permissions remain in force. New-only is the default. Updates require reviewing existing changes. The existing authenticated import API retains audit history and record identity, preventing duplicate rows on repeat upload. Master/Merge are saved by two requests; if one fails, the UI explains what was saved and allows a safe retry.

Validation: `node --test tests/invoice-import.test.js tests/role-import.test.js tests/import-portals.test.js` in backend; `node --test tests/invoice-service.test.js` and `npm run build` in frontend.
