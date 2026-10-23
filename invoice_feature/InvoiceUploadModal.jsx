import {useState} from 'react';
import Modal from '../common/Modal.jsx';
import {extractInvoice} from '../../services/invoiceService.js';

export default function InvoiceUploadModal({onClose,onPreview,onImport,user}) {
 const [file,setFile]=useState(null),[data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [newOnly,setNewOnly]=useState(true),[review,setReview]=useState(null);
 const executive=user.role==='executive';
 async function read(){
  setBusy(true);setError('');setData(null);setReview(null);
  try {setData(await extractInvoice(file));}catch(error){setError(error.message);}finally{setBusy(false);}
 }
 function common(field,value){
  setReview(null);setData(previous=>({...previous,master:previous.master.map(row=>({...row,[field]:value})),merge:previous.merge.map(row=>({...row,[field]:value}))}));
 }
 function edit(type,index,field,value){
  setReview(null);setData(previous=>({...previous,[type]:previous[type].map((row,i)=>i===index?{...row,[field]:value}:row)}));
 }
 async function submit(event){
  event.preventDefault();setBusy(true);setError('');
  try {
   if(!review){
    const master=await onPreview('master',data.master,newOnly);
    const merge=await onPreview('merge',data.merge,newOnly);
    setReview({master,merge});
   }else await onImport(data,newOnly);
  }catch(error){setError(error.message);}finally{setBusy(false);}
 }
 const commonFields=['Company','Portal','Invoice Number','Invoice Date','PO Number','Location'];
 return <Modal title="Upload invoice PDF" eyebrow="Master + Merge" onClose={()=>{if(!busy)onClose();}} onSubmit={submit}
  footer={<button className="button" disabled={busy||!data}>{busy?'Processing…':review?'Save to Master + Merge':'Review import'}</button>}>
  <label className="upload-zone">Choose invoice PDF (up to 10 MB)<input type="file" accept=".pdf,application/pdf" disabled={busy} onChange={event=>{setFile(event.target.files[0]||null);setData(null);setReview(null);setError('');}} /></label>
  <button type="button" className="button secondary" disabled={!file||busy} onClick={read}>{busy?'Reading invoice…':'Extract invoice'}</button>
  <p>PDF data stays on your inventory server. Review the extracted fields, then save both sheets with your existing permissions.</p>
  {error&&<p role="alert" className="error">{error}</p>}
  {data&&<>
   <div className="form-grid">{commonFields.map(field=><label key={field}>{field}<input disabled={busy} required={['Company','Portal','Invoice Number','Invoice Date'].includes(field)} type={field==='Invoice Date'?'date':'text'} value={data.master[0][field]??''} onChange={event=>common(field,event.target.value)} /></label>)}</div>
   {!executive&&<label><input type="checkbox" disabled={busy} checked={newOnly} onChange={event=>{setNewOnly(event.target.checked);setReview(null);}} /> Add new records only; keep existing records unchanged</label>}
   {executive&&<p>Executive access: existing records are skipped. Only new records will be added.</p>}
   {data.warnings?.map(warning=><p key={warning}>{warning}</p>)}
   {['master','merge'].map(type=><section key={type}><h3>{type==='master'?'Master shipment':'Merge invoice lines'} · {data[type].length} record(s)</h3>
    <div style={{overflowX:'auto',maxHeight:320}}><table><thead><tr>{Object.keys(data[type][0]).filter(field=>!commonFields.includes(field)).map(field=><th key={field}>{field}</th>)}</tr></thead>
     <tbody>{data[type].map((row,index)=><tr key={index}>{Object.entries(row).filter(([field])=>!commonFields.includes(field)).map(([field,value])=><td key={field}><input disabled={busy} aria-label={`${type} row ${index+1} ${field}`} value={value??''} style={{minWidth:130}} onChange={event=>edit(type,index,field,event.target.value)} /></td>)}</tr>)}</tbody>
    </table></div></section>)}
   {review&&<section><h3>Import review</h3>{['master','merge'].map(type=><div key={type}><p>{type}: {review[type].matchedCount||0} existing record(s). {newOnly?'Existing rows will be skipped.':'Existing nonblank changes below will be applied.'}</p>
    {!newOnly&&review[type].changes?.map((change,index)=><div key={index}><strong>Invoice {change.invoiceNumber}</strong>{change.differences?.map(diff=><p key={diff.field}>{diff.field}: {String(diff.existing??'(blank)')} → {String(diff.incoming??'(blank)')}</p>)}</div>)}</div>)}
    <p>Save writes both sheets through the existing authenticated shipment API. If one request fails, retry safely; existing records are matched instead of duplicated.</p>
   </section>}
  </>}
 </Modal>;
}
