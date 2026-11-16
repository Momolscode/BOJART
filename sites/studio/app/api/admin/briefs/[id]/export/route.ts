import { acquisitionService } from "../../../../../../lib/acquisition-runtime";
export const dynamic = "force-dynamic";
type Context = { params: Promise<{ id: string }> };
export async function GET(request: Request, context: Context) { return acquisitionService().export(request, (await context.params).id); }
