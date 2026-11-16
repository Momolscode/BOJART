import { acquisitionService } from "../../../lib/acquisition-runtime";
export const dynamic = "force-dynamic";
export async function POST(request: Request) { return acquisitionService().submit(request); }
