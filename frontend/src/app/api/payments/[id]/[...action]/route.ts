import { NextRequest, NextResponse } from 'next/server';
const allowedOrigins=(process.env.AUTH_ALLOWED_ORIGINS ?? 'http://localhost:3107,http://127.0.0.1:3107').split(',');
export async function POST(request:NextRequest,{params}:{params:Promise<{id:string;action:string[]}>}){
  const {id,action}=await params;
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id) || !(action.length===1 && action[0]==='start' || action.length===1 && action[0]==='check'))return NextResponse.json({detail:'Не найдено'},{status:404});
  const headers={'Cache-Control':'no-store'};
  const origin=request.headers.get('origin')??'';
  if(!allowedOrigins.includes(origin))return NextResponse.json({detail:'Недопустимый источник запроса'},{status:403,headers});
  if(!request.headers.get('content-type')?.startsWith('application/json'))return NextResponse.json({detail:'Ожидается JSON'},{status:415,headers});
  const session=request.cookies.get('pm_session')?.value;
  if(!session)return NextResponse.json({detail:'Войдите в аккаунт'},{status:401,headers});
  const reader=request.body?.getReader();if(!reader)return NextResponse.json({detail:'Пустой запрос'},{status:400,headers});
  const chunks:Uint8Array[]=[];let size=0;
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>4096){await reader.cancel();return NextResponse.json({detail:'Запрос слишком большой'},{status:413,headers});}chunks.push(value);}
  try{
    const paymentPath=action[0]==='start'?'platega-payment':'platega-payment/check';
    const upstream=await fetch(`${process.env.BACKEND_URL??'http://127.0.0.1:8107'}/api/v1/me/orders/${id}/${paymentPath}`,{method:'POST',headers:{'Content-Type':'application/json',Origin:origin,Cookie:`pm_session=${encodeURIComponent(session)}; pm_csrf=${encodeURIComponent(request.cookies.get('pm_csrf')?.value??'')}`,'X-CSRF-Token':request.headers.get('x-csrf-token')??''},body:Buffer.concat(chunks).toString('utf8'),cache:'no-store',redirect:'error',signal:AbortSignal.timeout(12000)});
    return new NextResponse(await upstream.text(),{status:upstream.status,headers:{...headers,'Content-Type':'application/json'}});
  }catch{return NextResponse.json({detail:'Сервис заказов временно недоступен'},{status:503,headers});}
}
export async function GET(request:NextRequest,{params}:{params:Promise<{id:string;action:string[]}>}){
  const {id,action}=await params;
  const headers={'Cache-Control':'no-store'};
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)||action.length!==1||action[0]!=='status')return NextResponse.json({detail:'Не найдено'},{status:404,headers});
  const session=request.cookies.get('pm_session')?.value;
  if(!session)return NextResponse.json({detail:'Войдите в аккаунт'},{status:401,headers});
  try{
    const upstream=await fetch(`${process.env.BACKEND_URL??'http://127.0.0.1:8107'}/api/v1/me/orders/${id}/platega-payment`,{headers:{Cookie:`pm_session=${encodeURIComponent(session)}`},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000)});
    return new NextResponse(await upstream.text(),{status:upstream.status,headers:{...headers,'Content-Type':'application/json'}});
  }catch{return NextResponse.json({detail:'Статус временно недоступен'},{status:503,headers});}
}
