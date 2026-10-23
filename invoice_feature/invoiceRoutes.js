import express from 'express';
import multer from 'multer';
import {extractInvoice} from '../services/invoiceParser.js';
const router=express.Router();
const upload=multer({storage:multer.memoryStorage(),limits:{fileSize:10*1024*1024,files:1}}).single('invoice');
router.post('/extract',(req,res)=>{
 upload(req,res,async error=>{
  if(error) return res.status(400).json({success:false,message:error.code==='LIMIT_FILE_SIZE'?'Invoice must be smaller than 10 MB.':'Unable to receive invoice PDF.'});
  if(!req.file || !req.file.buffer.subarray(0,5).equals(Buffer.from('%PDF-'))) return res.status(400).json({success:false,message:'Choose a valid PDF invoice.'});
  try {res.json({success:true,data:await extractInvoice(req.file.buffer,req.file.originalname)});}
  catch(error){res.status(error.status||422).json({success:false,message:error.status?error.message:'PDF could not be read. Upload a searchable, unencrypted invoice PDF.'});}
 });
});
export default router;
