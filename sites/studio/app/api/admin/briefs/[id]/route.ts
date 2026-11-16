import { acquisitionService } from "../../../../../lib/acquisition-runtime";
export const dynamic = "force-dynamic";
type Context = { params: Promise<{ id: string }> };
export async function GET(request: Request, context: Context) { return acquisitionService().detail(request, (await context.params).id); }
export async function PATCH(request: Request, context: Context) { return acquisitionService().update(request, (await context.params).id); }
export async function DELETE(request: Request, context: Context) { return acquisitionService().remove(request, (await context.params).id); }
