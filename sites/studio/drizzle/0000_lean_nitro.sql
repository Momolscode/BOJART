CREATE TABLE `inquiries` (
	`request_id` text PRIMARY KEY NOT NULL,
	`reference` text NOT NULL,
	`payload_hash` text NOT NULL,
	`payload_json` text NOT NULL,
	`status` text DEFAULT 'new' NOT NULL,
	`revision` integer DEFAULT 1 NOT NULL,
	`created_at` integer NOT NULL,
	`updated_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `inquiries_reference_unique` ON `inquiries` (`reference`);--> statement-breakpoint
CREATE INDEX `inquiries_created_idx` ON `inquiries` (`created_at`,`request_id`);--> statement-breakpoint
CREATE INDEX `inquiries_status_idx` ON `inquiries` (`status`,`created_at`);--> statement-breakpoint
CREATE TABLE `inquiry_rate_limits` (
	`key` text PRIMARY KEY NOT NULL,
	`count` integer DEFAULT 0 NOT NULL,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE INDEX `inquiry_rate_expiry_idx` ON `inquiry_rate_limits` (`expires_at`);--> statement-breakpoint
CREATE TABLE `inquiry_tombstones` (
	`request_id` text PRIMARY KEY NOT NULL,
	`deleted_at` integer NOT NULL
);
