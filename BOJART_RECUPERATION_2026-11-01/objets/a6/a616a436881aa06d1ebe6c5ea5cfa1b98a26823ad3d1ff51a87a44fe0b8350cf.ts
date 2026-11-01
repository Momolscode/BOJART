import { env } from "cloudflare:workers";
import { createAcquisitionService, authorizedAdmin } from "./acquisition-service.mjs";

type RuntimeEnv = { DB?: D1Database; BOJART_ADMIN_EMAILS?: string; BOJART_FORM_SECRET?: string };
const runtimeEnv = () => env as RuntimeEnv;

export function acquisitionService() {
  const values = runtimeEnv();
  return createAcquisitionService({ db: values.DB, secret: values.BOJART_FORM_SECRET, adminEmails: values.BOJART_ADMIN_EMAILS });
}

export function isAcquisitionAdmin(identity: { userId: string; email: string } | null) {
  return authorizedAdmin(identity, runtimeEnv().BOJART_ADMIN_EMAILS);
}
