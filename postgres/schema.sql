-- Adminer 4.8.1 PostgreSQL 15.4 dump

CREATE TABLE "public"."accounts" (
    "id" uuid NOT NULL,
    "debits_pending" numeric(40,0) NOT NULL,
    "debits_posted" numeric(40,0) NOT NULL,
    "credits_pending" numeric(40,0) NOT NULL,
    "credits_posted" numeric(40,0) NOT NULL,
    "user_data_128" bit(128) NOT NULL,
    "user_data_64" bit(64) NOT NULL,
    "user_data_32" bit(32) NOT NULL,
    "ledger" integer NOT NULL,
    "code" smallint NOT NULL,
    "flags" bit(16) NOT NULL,
    "timestamp" bigint NOT NULL,
    CONSTRAINT "accounts_id" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "accounts_code" ON "public"."accounts" USING btree ("code");

CREATE INDEX "accounts_credits_pending" ON "public"."accounts" USING btree ("credits_pending");

CREATE INDEX "accounts_credits_posted" ON "public"."accounts" USING btree ("credits_posted");

CREATE INDEX "accounts_debits_pending" ON "public"."accounts" USING btree ("debits_pending");

CREATE INDEX "accounts_debits_posted" ON "public"."accounts" USING btree ("debits_posted");

CREATE INDEX "accounts_flags" ON "public"."accounts" USING btree ("flags");

CREATE INDEX "accounts_ledger" ON "public"."accounts" USING btree ("ledger");

CREATE INDEX "accounts_timestamp" ON "public"."accounts" USING btree ("timestamp");

CREATE INDEX "accounts_user_data_128" ON "public"."accounts" USING btree ("user_data_128");

CREATE INDEX "accounts_user_data_32" ON "public"."accounts" USING btree ("user_data_32");

CREATE INDEX "accounts_user_data_64" ON "public"."accounts" USING btree ("user_data_64");


CREATE TABLE "public"."transfers" (
    "id" uuid NOT NULL,
    "debit_account_id" uuid NOT NULL,
    "credit_account_id" uuid NOT NULL,
    "amount" numeric(40,0) NOT NULL,
    "pending_id" uuid,
    "user_data_128" bit(128) NOT NULL,
    "user_data_64" bit(64) NOT NULL,
    "user_data_32" bit(32) NOT NULL,
    "timeout" integer NOT NULL,
    "ledger" integer NOT NULL,
    "code" smallint NOT NULL,
    "flags" bit(16) NOT NULL,
    "timestamp" bigint NOT NULL,
    CONSTRAINT "transfers_id" PRIMARY KEY ("id")
) WITH (oids = false);

CREATE INDEX "transfers_amount" ON "public"."transfers" USING btree ("amount");

CREATE INDEX "transfers_code" ON "public"."transfers" USING btree ("code");

CREATE INDEX "transfers_credit_account_id" ON "public"."transfers" USING btree ("credit_account_id");

CREATE INDEX "transfers_debit_account_id" ON "public"."transfers" USING btree ("debit_account_id");

CREATE INDEX "transfers_flags" ON "public"."transfers" USING btree ("flags");

CREATE INDEX "transfers_ledger" ON "public"."transfers" USING btree ("ledger");

CREATE INDEX "transfers_pending_id" ON "public"."transfers" USING btree ("pending_id");

CREATE INDEX "transfers_timeout" ON "public"."transfers" USING btree ("timeout");

CREATE INDEX "transfers_timestamp" ON "public"."transfers" USING btree ("timestamp");

CREATE INDEX "transfers_user_data_128" ON "public"."transfers" USING btree ("user_data_128");

CREATE INDEX "transfers_user_data_32" ON "public"."transfers" USING btree ("user_data_32");

CREATE INDEX "transfers_user_data_64" ON "public"."transfers" USING btree ("user_data_64");


ALTER TABLE ONLY "public"."transfers" ADD CONSTRAINT "transfers_credit_account_id_fkey" FOREIGN KEY (credit_account_id) REFERENCES accounts(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."transfers" ADD CONSTRAINT "transfers_debit_account_id_fkey" FOREIGN KEY (debit_account_id) REFERENCES accounts(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;
ALTER TABLE ONLY "public"."transfers" ADD CONSTRAINT "transfers_pending_id_fkey" FOREIGN KEY (pending_id) REFERENCES accounts(id) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE;

-- 2023-10-25 17:58:37.364287+02
