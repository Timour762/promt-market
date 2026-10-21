// Server/runtime flag: never expose deployment secrets through NEXT_PUBLIC_*.
export function isPublicPreview(): boolean {
  return process.env.PUBLIC_PREVIEW === 'true';
}
