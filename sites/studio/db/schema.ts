import { integer, sqliteTable, text, index } from "drizzle-orm/sqlite-core";

// Server-owned records; no raw network address, session, or form token is stored.
export const inquiries = sqliteTable("inquiries", {
  requestId: text("request_id").primaryKey(),
  reference: text("reference").notNull().unique(),
  payloadHash: text("payload_hash").notNull(),
  payloadJson: text("payload_json").notNull(),
  privacyVersion: text("privacy_version").notNull().default("2026-10-19"),
  status: text("status").notNull().default("new"),
  revision: integer("revision").notNull().default(1),
  createdAt: integer("created_at").notNull(),
  updatedAt: integer("updated_at").notNull(),
}, (table) => [
  index("inquiries_created_idx").on(table.createdAt, table.requestId),
  index("inquiries_status_idx").on(table.status, table.createdAt),
]);

// Daily HMAC keys enforce intake limits without persisting raw IP addresses.
export const inquiryRateLimits = sqliteTable("inquiry_rate_limits", {
  key: text("key").primaryKey(),
  count: integer("count").notNull().default(0),
  expiresAt: integer("expires_at").notNull(),
}, (table) => [index("inquiry_rate_expiry_idx").on(table.expiresAt)]);

// Prevent a delayed retry from recreating an erased brief. No contact data/hash.
export const inquiryTombstones = sqliteTable("inquiry_tombstones", {
  requestId: text("request_id").primaryKey(),
  deletedAt: integer("deleted_at").notNull(),
});
