import {parseTallyInvoice} from './tallyInvoiceParser.js';
import {parseAlternateInvoice} from './alternateInvoiceParser.js';
import { getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs';
import {portalName} from '../utils/importIdentity.js';
import { badRequest, validateRecord } from '../utils/shipmentRecords.js';

const money = value => {
 const raw = String(value).replace(/[ ,]/g, '');
 if (!/^\d+(?:\.\d+)?$/.test(raw)) throw badRequest('Unreadable invoice amount. Review the PDF layout.');
 return Number(raw);
};
const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
const dateValue = value => {
 const match = clean(value).match(/^(\d{1,2})-([A-Za-z]{3})-(\d{4})$/);
 const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
 const month = match ? months.findIndex(m => m.toLowerCase() === match[2].toLowerCase()) + 1 : 0;
 if (!month) throw badRequest('Invoice date could not be read.');
 const result = `${match[3]}-${String(month).padStart(2,'0')}-${match[1].padStart(2,'0')}`;
 if (new Date(result).toISOString().slice(0,10) !== result) throw badRequest('Invalid invoice date.');
 return result;
};

export function parseInvoicePages(pages, filename = '') {
 const all = pages.flat();
 if (all.some(item=>/^Consignee \(Ship to\)$/i.test(item.text))) return parseTallyInvoice(pages,filename);
 if (all.some(item=>/^Invoice Code:/i.test(item.text))) return parseAlternateInvoice(pages,filename);
 const find = pattern => all.find(item => pattern.test(item.text));
 const below = label => {
  if (!label) return '';
  return all.filter(item => item.page === label.page && item.y > label.y + 2 && item.y < label.y + 25 && Math.abs(item.x-label.x)<8)
   .sort((a,b)=>a.y-b.y).map(item=>item.text).join(' ');
 };
 const invoice = below(find(/^Invoice No:$/i));
 const invoiceDate = dateValue(below(find(/^Invoice Date:?$/i)));
 const order = find(/^Order No:/i)?.text.replace(/^Order No:\s*/i,'') || '';
 const orderDateText = find(/^Order Date:/i)?.text.replace(/^Order Date:\s*/i,'');
 const portalLabel = find(/^Portal:$/i);
 const portalValue = portalLabel ? all.find(item => item.page===portalLabel.page && Math.abs(item.y-portalLabel.y)<2 && item.x>portalLabel.x+20)?.text : '';
 const billTo=below(find(/^Bill To:$/i));
 const portal=portalName(portalValue || billTo);
 const sellerStart = find(/^Invoice No:$/i);
 const seller = sellerStart ? all.filter(item => item.page===sellerStart.page && item.x<sellerStart.x-20 && item.y>=sellerStart.y-2 && item.y<sellerStart.y+25)
  .sort((a,b)=>a.y-b.y).map(item=>item.text).join(' ') : '';
 const ship = find(/^Ship To:$/i);
 const address = ship ? all.filter(item=>item.page===ship.page && item.x>=ship.x-2 && item.x<410 && item.y>ship.y && item.y<ship.y+130)
  .sort((a,b)=>a.y-b.y||a.x-b.x) : [];
 const locationLine = address.find(item=>/\b\d{6}\b/.test(item.text));
 const destination = locationLine ? clean(locationLine.text.split(/\b\d{6}\b/)[0]).replace(/,$/,'') : '';
 const pin = locationLine?.text.match(/\b\d{6}\b/)?.[0] || '';
 const warehouse = address.find(item=>/^[A-Z]{3}\d,?$/.test(item.text))?.text.replace(/,$/,'') || '';
 const boxLabel = find(/^Box Count\s*:/i);
 const boxes = boxLabel ? all.find(item=>item.page===boxLabel.page && Math.abs(item.y-boxLabel.y)<2 && item.x>boxLabel.x+45)?.text : '';
 const table = find(/^Channel Product ID$/i);
 if (!invoice || !seller || !portal || !table) throw badRequest('This PDF does not match the supported invoice layout. Upload a searchable invoice with invoice number, company, portal and item table.');
 const qtyHeader = all.find(item=>item.page===table.page && Math.abs(item.y-table.y)<2 && item.text==='Qty');
 if (!qtyHeader) throw badRequest('Invoice quantity column is missing.');
 const starts = all.filter(item=>item.x<35 && /^\d+$/.test(item.text) && (item.page>table.page || item.y>table.y+25))
  .filter(item=>all.some(other=>other.page===item.page && Math.abs(other.y-item.y)<2 && other.x>table.x && other.x<qtyHeader.x && /^B[A-Z0-9]{9}$/.test(other.text)))
  .sort((a,b)=>a.page-b.page||a.y-b.y);
 if (!starts.length) throw badRequest('No readable invoice line items found. Scanned PDFs require OCR and are not supported yet.');
 const firstValues = all.filter(item=>item.page===starts[0].page && Math.abs(item.y-starts[0].y)<2 && item.x>qtyHeader.x-10 && /^\d[\d,.]*$/.test(item.text)).sort((a,b)=>a.x-b.x);
 if (firstValues.length!==5) throw badRequest('The invoice financial columns could not be identified.');
 const lefts=firstValues.map(item=>item.x-2);
 const common = {Company:clean(seller),Portal:clean(portal),'PO Number':clean(order),Location:destination,'Invoice Number':invoice,'Invoice Date':invoiceDate,'Import Source':'Invoice PDF'};
 const merge = starts.map((start,index)=>{
  const next=starts[index+1];
  const region=all.filter(item=>item.page>=start.page && (!next || item.page<=next.page) &&
   (item.page!==start.page || item.y>=start.y-2) && (!next || item.page!==next.page || item.y<next.y-2));
  const metadataX=Math.min(...region.filter(item=>/^HSN code:/i.test(item.text)).map(item=>item.x));
  if (!Number.isFinite(metadataX)) throw badRequest('An invoice line is missing HSN metadata.');
  const title=region.filter(item=>item.x>35 && item.x<metadataX-1 && !/^Total:/.test(item.text))
   .filter(item=>item.page===start.page && item.y<start.y+130).sort((a,b)=>a.y-b.y||a.x-b.x).map(item=>item.text).join(' ');
  const meta = pattern => {
   const label=region.find(item=>pattern.test(item.text));
   if (!label) return '';
   return region.find(item=>item.page===label.page && Math.abs(item.y-label.y)<2 && item.x>label.x+20 && !pattern.test(item.text))?.text || below(label);
  };
  const values=lefts.map((left,column)=>{
   const cell=region.filter(item=>item.page===start.page && item.y<=start.y+25 && item.x>=left && item.x<(lefts[column+1]??1000) && /^\d[\d,.]*$/.test(item.text))
    .sort((a,b)=>a.y-b.y||a.x-b.x).map(item=>item.text).join('');
   return money(cell);
  });
  const asin=region.find(item=>/^B[A-Z0-9]{9}$/.test(item.text))?.text;
  const percent=region.find(item=>item.page===start.page && item.y<start.y+25 && /\([\d.]+\)\s*%/.test(item.text))?.text.match(/[\d.]+/)?.[0];
  const line={...common,ASIN:asin,EAN:meta(/^EAN\s*:/i),'SKU Code':meta(/^Seller Sku Code\s*:/i),'Product Name':clean(title),'HSN Code':meta(/^HSN code:/i),Qty:values[0],'Unit Cost':values[1],'Total Cost':values[2],IGST:percent?Number(percent):null,CGST:null,SGST:null,'IGST Amount':values[3],'Total Amount':values[4]};
  if (!line['SKU Code'] || !/^\d{8,14}$/.test(line.EAN) || !line.Qty || !line['Product Name']) throw badRequest('An invoice item is incomplete; no records were imported.');
  if (Math.abs(line['Total Cost']+line['IGST Amount']-line['Total Amount'])>0.02) throw badRequest('Invoice line totals do not reconcile.');
  return validateRecord('merge',line);
 });
 const totals=merge.reduce((sum,row)=>({qty:sum.qty+row.Qty,taxable:sum.taxable+row['Total Cost'],tax:sum.tax+row['IGST Amount'],total:sum.total+row['Total Amount']}),{qty:0,taxable:0,tax:0,total:0});
 const totalLabel=find(/^Total:$/);
 if (!totalLabel) throw badRequest('Invoice total is missing.');
 const printedTotals=lefts.map((left,column)=>{
  const cell=all.filter(item=>item.page===totalLabel.page && item.y>=totalLabel.y-2 && item.y<totalLabel.y+25 && item.x>=left && item.x<(lefts[column+1]??1000) && /^\d[\d,.]*$/.test(item.text)).sort((a,b)=>a.y-b.y||a.x-b.x).map(item=>item.text).join('');
  return cell?money(cell):null;
 });
 for (const [actual,printed] of [[totals.qty,printedTotals[0]],[totals.taxable,printedTotals[2]],[totals.tax,printedTotals[3]],[totals.total,printedTotals[4]]]) {
  if (printed===null || Math.abs(actual-printed)>0.02) throw badRequest('Extracted rows do not match the printed invoice totals.');
 }
 const master=validateRecord('master',{...common,'Vendor Code/ Shipment Id':'','PO Date':'',Qty:totals.qty,Parcel:boxes?Number(boxes):null,'Invoice Value':Number(totals.total.toFixed(2)),'Without Tax Amount':Number(totals.taxable.toFixed(2)),'Tax Amount':Number(totals.tax.toFixed(2)),'Destination PIN':pin,'E-Way Bill Number':find(/^\d{12}$/)?.text||''});
 return {filename,master:[master],merge,warnings:['Review extracted fields before saving. Invoice quantity does not automatically change warehouse stock. Missing logistics/status fields are left blank.']};
}

export async function extractInvoice(buffer,filename) {
 let document;
 try {
  document=await getDocument({data:new Uint8Array(buffer),useSystemFonts:true,isEvalSupported:false}).promise;
  if (document.numPages>20) throw badRequest('Upload an invoice with at most 20 pages.');
  const pages=[];
  for (let pageNumber=1;pageNumber<=document.numPages;pageNumber++) {
   const page=await document.getPage(pageNumber);const content=await page.getTextContent();
   pages.push(content.items.filter(item=>item.str?.trim()).map(item=>({text:clean(item.str),x:item.transform[4],y:page.view[3]-item.transform[5],page:pageNumber})));
  }
  return parseInvoicePages(pages,filename);
 } finally { if(document) await document.destroy(); }
}
