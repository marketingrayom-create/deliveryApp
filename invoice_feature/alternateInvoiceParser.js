import {badRequest,validateRecord} from '../utils/shipmentRecords.js';
import {portalName} from '../utils/importIdentity.js';

export function parseAlternateInvoice(pages,filename='') {
 const all=pages.flat().sort((a,b)=>a.page-b.page||a.y-b.y||a.x-b.x);
 const find=pattern=>all.find(item=>pattern.test(item.text));
 const value=pattern=>{
  const label=find(pattern);if(!label)return '';
  const inline=label.text.replace(pattern,'').trim();if(inline)return inline;
  return all.find(item=>item.page===label.page&&Math.abs(item.y-label.y)<2&&item.x>label.x+20)?.text||'';
 };
 const date=text=>{
  const months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
  const match=text.match(/^(\d{1,2})[- /]([A-Za-z]{3})[- /](\d{4})$/);
  const month=match?months.indexOf(match[2].toLowerCase())+1:0;
  if(!month)throw badRequest('Invoice date could not be read.');
  const result=`${match[3]}-${String(month).padStart(2,'0')}-${match[1].padStart(2,'0')}`;
  if(new Date(result).toISOString().slice(0,10)!==result)throw badRequest('Invalid invoice date.');
  return result;
 };
 const below=(label,maxHeight)=>label?all.filter(item=>item.page===label.page&&Math.abs(item.x-label.x)<5&&item.y>label.y+2&&item.y<label.y+maxHeight).map(item=>item.text):[];
 const company=below(find(/^Sender:$/i),31).join(' ');
 const billTo=below(find(/^Bill To:$/i),20)[0]||'';
 const ship=find(/^Ship To:$/i);
 const address=below(ship,110);
 const destination=address.find(text=>/\d{6}/.test(text))||'';
 const state=address.find(text=>/\([0-9]{2}\).*India/i.test(text))?.replace(/\s*\(\d{2}\).*$/,'')||'';
 const header=find(/^Description of Goods$/i);
 const qtyHeader=find(/^Qty$/i);
 if(!company||!billTo||!header||!qtyHeader)throw badRequest('Invoice header or item table could not be read.');
 const invoice=value(/^Invoice Code:\s*/i);
 const common={Company:company,Portal:portalName(value(/^Portal:\s*/i)||billTo),'Invoice Number':invoice,'Invoice Date':date(value(/^Invoice Date:\s*/i)),'PO Number':value(/^Order No:\s*/i),Location:destination.replace(/\s*-?\s*\d{6}.*$/,'').trim(),'Import Source':'Invoice PDF'};
 const starts=all.filter(item=>item.x<=40&&/^\d+$/.test(item.text)&&(item.page>header.page||item.y>header.y+20))
  .filter(item=>all.some(other=>other.page===item.page&&Math.abs(other.y-item.y)<2&&other.x>qtyHeader.x-5&&/^\d[\d,.]*$/.test(other.text)));
 if(!starts.length)throw badRequest('Invoice has no readable item lines.');
 const total=find(/^Total:$/i);if(!total)throw badRequest('Printed invoice totals are missing.');
 const numeric=text=>/^\d[\d,.]*$/.test(text);
 const first=all.filter(item=>item.page===starts[0].page&&Math.abs(item.y-starts[0].y)<2&&item.x>qtyHeader.x-5&&numeric(item.text)).sort((a,b)=>a.x-b.x);
 const totalCells=all.filter(item=>item.page===total.page&&Math.abs(item.y-total.y)<2&&item.x>qtyHeader.x-5&&numeric(item.text)).sort((a,b)=>a.x-b.x);
 if(first.length!==5||totalCells.length!==4)throw badRequest('Invoice financial columns could not be identified.');
 const lefts=first.map((item,index)=>Math.min(item.x,index===1?item.x:totalCells[index===0?0:index-1].x)-2);
 const number=text=>{const raw=text.replace(/[,\s]/g,'');if(!/^\d+(?:\.\d+)?$/.test(raw))throw badRequest('Unreadable invoice amount.');return Number(raw);};
 const merge=starts.map((start,index)=>{
  const next=starts[index+1];
  const region=all.filter(item=>item.page>=start.page&&(!next||item.page<=next.page)&&(item.page!==start.page||item.y>=start.y-2)&&(!next||item.page!==next.page||item.y<next.y-2)&&
   (item.page<total.page||item.y<total.y-2));
  const hsn=region.find(item=>/^HSN Code:/i.test(item.text));
  const meta=pattern=>{const label=region.find(item=>pattern.test(item.text));if(!label)return '';const text=label.text.replace(pattern,'').trim();return text||region.find(item=>item.page===label.page&&Math.abs(item.y-label.y)<2&&item.x>label.x)?.text||'';};
  const title=region.filter(item=>item.x>45&&item.x<qtyHeader.x-50&&(item.page!==hsn?.page||item.y<hsn.y-2)&&!/^ASIN:|^EAN:|^HSN Code:/i.test(item.text))
   .map(item=>item.text).join(' ');
  const values=lefts.map((left,column)=>number(region.filter(item=>item.page===start.page&&item.y<start.y+25&&item.x>=left&&item.x<(lefts[column+1]??1000)&&numeric(item.text)).map(item=>item.text).join('')));
  const percent=region.find(item=>item.y<start.y+25&&/\([\d.]+%\)/.test(item.text))?.text.match(/[\d.]+/)?.[0];
  const fields={...common,'Product Name':title,ASIN:meta(/^ASIN:\s*/i),EAN:meta(/^EAN:\s*/i),'SKU Code':meta(/^Seller Sku Code:\s*/i),'HSN Code':meta(/^HSN Code:\s*/i),Qty:values[0],'Unit Cost':values[1],'Total Cost':values[2],'IGST Amount':values[3],'Total Amount':values[4],IGST:percent?Number(percent):null,CGST:null,SGST:null};
  if(!fields['Product Name']||!/^B[A-Z0-9]{9}$/.test(fields.ASIN)||!fields.Qty||Math.abs(values[2]+values[3]-values[4])>0.02)throw badRequest('Invoice line is incomplete or totals do not reconcile.');
  return validateRecord('merge',fields);
 });
 const sums=merge.reduce((s,row)=>[s[0]+row.Qty,s[1]+row['Total Cost'],s[2]+row['IGST Amount'],s[3]+row['Total Amount']],[0,0,0,0]);
 sums.forEach((sum,index)=>{if(Math.abs(sum-number(totalCells[index].text))>0.02)throw badRequest('Extracted rows do not match the printed invoice totals.');});
 const box=value(/^Box Count\s*:\s*/i);
 const master=validateRecord('master',{...common,State:state,Qty:sums[0],Parcel:box?number(box):null,'Without Tax Amount':Number(sums[1].toFixed(2)),'Tax Amount':Number(sums[2].toFixed(2)),'Invoice Value':Number(sums[3].toFixed(2))});
 return {filename,master:[master],merge,warnings:['Review before saving. Missing fields remain blank; Order Date is not treated as PO Date. SKU remains blank when the invoice does not provide it.']};
}
