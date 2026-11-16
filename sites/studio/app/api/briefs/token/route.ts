import { acquisitionService } from "../../../../lib/acquisition-runtime";
export const dynamic = "force-dynamic";
export async function GET(request: Request) { return acquisitionService().token(request); }
