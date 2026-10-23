import {apiFetch} from './apiClient.js';
import {readApiResponse} from './apiResponse.js';
export async function extractInvoice(file) {
 const body=new FormData();body.append('invoice',file);
 const response=await apiFetch('/invoices/extract',{method:'POST',body});
 const result=await readApiResponse(response);
 if(!response.ok) throw Error(result.message || 'Invoice could not be read.');
 return result.data;
}
