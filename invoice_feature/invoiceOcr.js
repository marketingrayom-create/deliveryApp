import {createCanvas} from '@napi-rs/canvas';
import {createWorker,PSM} from 'tesseract.js';
import english from '@tesseract.js-data/eng';

export async function recoverOutlinedAsins(document,pages){
 let worker;const recovered=[];
 try{
  for(let index=0;index<pages.length;index++){
   const items=pages[index];
   const labels=items.filter(item=>/^ASIN\s*:\s*$/i.test(item.text)&&!items.some(other=>Math.abs(other.y-item.y)<3&&/^B[A-Z0-9]{9}$/.test(other.text)));
   if(!labels.length)continue;
   worker ||= await createWorker('eng',1,{langPath:english.langPath,gzip:true,cacheMethod:'none'});
   await worker.setParameters({tessedit_pageseg_mode:PSM.SINGLE_LINE,tessedit_char_whitelist:'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'});
   const page=await document.getPage(index+1),scale=4,viewport=page.getViewport({scale});
   const canvas=createCanvas(Math.ceil(viewport.width),Math.ceil(viewport.height));
   await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
   for(const label of labels){
    const x=Math.max(0,Math.floor((label.x+(label.width||25))*scale));
    const y=Math.max(0,Math.floor((label.y-14)*scale));
    const width=Math.min(Math.ceil(175*scale),canvas.width-x),height=Math.min(22*scale,canvas.height-y);
    if(width<=0||height<=0)continue;
    const crop=createCanvas(width,height);crop.getContext('2d').drawImage(canvas,x,y,width,height,0,0,width,height);
    const result=await worker.recognize(crop.toBuffer('image/png'));
    const text=result.data.text.replace(/\s+/g,'').trim();
    if(result.data.confidence>=65&&/^B[A-Z0-9]{9}$/.test(text)){
     items.push({text,x:label.x+(label.width||25)+1,y:label.y,page:index+1});
     recovered.push(text);
    }
   }
  }
 }finally{if(worker)await worker.terminate();}
 return recovered;
}

export function applyRequestedTaxSplit(result){
 for(const row of result.merge){
  if(typeof row.IGST==='number'&&Number.isFinite(row.IGST)){
   row.CGST=row.IGST/2;row.SGST=row.IGST/2;
  }
 }
 result.warnings.push('CGST/SGST percentages are derived as half of the printed GST rate. Original invoice tax amounts are preserved.');
 return result;
}
