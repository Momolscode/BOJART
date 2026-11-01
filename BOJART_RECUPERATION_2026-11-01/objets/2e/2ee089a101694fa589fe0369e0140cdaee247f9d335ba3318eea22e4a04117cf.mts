export type AcquisitionService = {
  token(request: Request): Promise<Response>;
  submit(request: Request): Promise<Response>;
  list(request: Request): Promise<Response>;
  detail(request: Request, id: string): Promise<Response>;
  update(request: Request, id: string): Promise<Response>;
  remove(request: Request, id: string): Promise<Response>;
  export(request: Request, id: string): Promise<Response>;
};
export function createAcquisitionService(options?: {
  db?: D1Database;
  secret?: string;
  adminEmails?: string;
  now?: () => number;
  cryptoImpl?: Crypto;
}): AcquisitionService;
export function authorizedAdmin(identity: { userId: string; email: string } | null | undefined, allowlist?: string): boolean;
export function requireSameOrigin(request: Request): void;
export function readBoundedJSON(request: Request, limit?: number): Promise<unknown>;
