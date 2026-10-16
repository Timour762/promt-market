import { NextResponse } from 'next/server';
export async function GET(){
 try{
  const response=await fetch(`${process.env.BACKEND_URL??'http://127.0.0.1:8107'}/ready`,{cache:'no-store',signal:AbortSignal.timeout(3000)});
  return NextResponse.json({status:response.ok?'ready':'unavailable'},{status:response.ok?200:503,headers:{'Cache-Control':'no-store'}});
 }catch{return NextResponse.json({status:'unavailable'},{status:503,headers:{'Cache-Control':'no-store'}});}
}
