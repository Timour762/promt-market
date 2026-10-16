import { NextRequest, NextResponse } from 'next/server';
export async function GET(request:NextRequest,{params}:{params:Promise<{id:string}>}){
  const {id}=await params;const headers={'Cache-Control':'no-store'};
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id))return new NextResponse('Не найдено',{status:404,headers});
  const session=request.cookies.get('pm_session')?.value;
  if(!session)return NextResponse.json({detail:'Войдите в аккаунт'},{status:401,headers});
  try{
    const upstream=await fetch(`${process.env.BACKEND_URL??'http://127.0.0.1:8107'}/api/v1/me/library/${id}/download`,{headers:{Cookie:`pm_session=${encodeURIComponent(session)}`},cache:'no-store',redirect:'error',signal:AbortSignal.timeout(12000)});
    if(!upstream.ok)return NextResponse.json({detail:upstream.status===404?'Промпт не найден':'Не удалось скачать текст'},{status:upstream.status,headers});
    return new NextResponse(await upstream.text(),{headers:{...headers,'Content-Type':'text/plain; charset=utf-8','Content-Disposition':`attachment; filename="prompt-${id}.txt"`,'X-Content-Type-Options':'nosniff'}});
  }catch{return NextResponse.json({detail:'Сервис временно недоступен'},{status:503,headers});}
}
