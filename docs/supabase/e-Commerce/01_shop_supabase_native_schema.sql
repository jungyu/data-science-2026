-- ============================================================
-- Supabase-Native E-Commerce Schema  v3.0
-- Stage-by-Stage Learning Edition
-- ============================================================
--
-- Conventions (aligned with project skill guidelines):
--   - PK: TEXT DEFAULT generate_ulid()  (not BIGINT, not UUID)
--   - FK: TEXT references (type consistency)
--   - Auth bridge: users table (ULID) + auth_user_id (UUID)
--   - business tables NEVER reference auth.users directly
--   - RLS: helper functions, no inline JOIN/EXISTS
--   - Every table: RLS enabled + policies + GRANTs + service_role
--   - auth.uid() wrapped as (SELECT auth.uid()) in policies
--   - CHECK constraints named explicitly
--   - Soft-delete via deleted_at on core tables (not append-heavy)
--   - moddatetime for updated_at
--   - security definer + set search_path on all functions
--
-- ============================================================
-- Table of Contents:
--   Stage 1: Foundation (extensions, ULID, types, helpers)
--   Stage 2: Identity (users bridge, profiles)
--   Stage 3: Organization (companies, stores, store_staff)
--   Stage 4: Catalog (products, product_images, reviews)
--   Stage 5: Taxonomy (terms, term_taxonomy, term_relationships)
--   Stage 6: Inventory (stocks, inventory_movements)
--   Stage 7: Coupons & Addresses
--   Stage 8: Commerce (orders, order_items, order_coupons, payments, points)
--   Stage 9: Security (RLS helpers, policies, GRANTs)
--   Stage 10: Automation (triggers, realtime, storage)
-- ============================================================


-- ************************************************************
-- STAGE 1: FOUNDATION
-- ************************************************************
-- Learn: Extensions, ID generation, custom types, base helpers.
-- Why ULID? Sortable by time, B-Tree friendly, 26 chars.
-- Why enums? Database-level validation, no invalid status values.
-- ************************************************************

-- Extensions
create extension if not exists pgcrypto;
create extension if not exists moddatetime;
create extension if not exists pg_trgm;

-- ULID generator (26-char Crockford Base32, time-sortable)
-- Returns TEXT — all business PKs and FKs use TEXT for consistency.
create or replace function public.generate_ulid()
returns text
language plpgsql
volatile
as $$
declare
  timestamp  bigint;
  output     text := '';
  unix_ts    bigint;
  encoding   char[] := string_to_array('0123456789ABCDEFGHJKMNPQRSTVWXYZ', null);
  i          int;
  rand_bytes bytea;
begin
  unix_ts := (extract(epoch from clock_timestamp()) * 1000)::bigint;

  -- Encode 48-bit timestamp (10 chars)
  for i in reverse 9..0 loop
    output := output || encoding[1 + (unix_ts % 32)::int];
    unix_ts := unix_ts >> 5;
  end loop;

  -- Encode 80-bit random (16 chars)
  rand_bytes := gen_random_bytes(10);
  for i in 0..9 loop
    output := output || encoding[1 + (get_byte(rand_bytes, i) % 32)];
  end loop;

  return output;
end;
$$;

-- Custom enum types
do $$ begin create type public.company_type    as enum ('retailer','wholesaler','manufacturer','distributor');              exception when duplicate_object then null; end $$;
do $$ begin create type public.product_status  as enum ('draft','publish','archived','trash');                              exception when duplicate_object then null; end $$;
do $$ begin create type public.product_type    as enum ('physical','digital','virtual','grouped','variable');               exception when duplicate_object then null; end $$;
do $$ begin create type public.order_status    as enum ('pending','confirmed','processing','shipped','delivered','cancelled','refunded'); exception when duplicate_object then null; end $$;
do $$ begin create type public.payment_status  as enum ('pending','processing','paid','failed','refunded','partially_refunded','cancelled'); exception when duplicate_object then null; end $$;
do $$ begin create type public.payment_method  as enum ('credit_card','debit_card','line_pay','apple_pay','google_pay','bank_transfer','cash_on_delivery','points'); exception when duplicate_object then null; end $$;
do $$ begin create type public.discount_type   as enum ('fixed','percentage','free_shipping');                              exception when duplicate_object then null; end $$;
do $$ begin create type public.movement_reason as enum ('sale','return','restock','adjustment','manual','transfer');        exception when duplicate_object then null; end $$;
do $$ begin create type public.address_label   as enum ('home','office','shipping','billing','other');                      exception when duplicate_object then null; end $$;

-- Audit fields trigger (auto-fill created_by / updated_by)
create or replace function public.handle_audit_fields()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'INSERT' then
    new.created_by = coalesce(new.created_by, public.get_current_user_id());
    new.updated_by = coalesce(new.updated_by, public.get_current_user_id());
  elsif tg_op = 'UPDATE' then
    new.updated_by = coalesce(public.get_current_user_id(), new.updated_by);
  end if;
  return new;
end;
$$;


-- ************************************************************
-- STAGE 2: IDENTITY
-- ************************************************************
-- Learn: Auth bridge pattern.
--   auth.users (Supabase-managed, UUID PK)
--     ↕  bridge
--   users (ULID PK, auth_user_id UUID) ← all business FKs point here
--     ↕  extends
--   profiles (optional extra data)
--
-- Why a bridge? Business tables never directly reference auth.users.
-- This decouples your schema from Supabase internals and keeps
-- all FK types as TEXT (ULID).
-- ************************************************************

create table if not exists public.users (
  id            text primary key default generate_ulid(),
  auth_user_id  uuid unique not null references auth.users(id) on delete cascade,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists idx_users_auth on public.users(auth_user_id);

-- Bridge helper: auth UUID → ULID user ID (cached per statement)
create or replace function public.get_current_user_id()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select id from public.users where auth_user_id = (select auth.uid()) limit 1;
$$;

grant execute on function public.get_current_user_id() to authenticated;

-- Profiles (extended user data)
create table if not exists public.profiles (
  id           text primary key references public.users(id) on delete cascade,
  username     varchar(60)  not null,
  full_name    varchar(250) not null default '',
  display_name varchar(250) not null default '',
  avatar_url   text,
  phone        varchar(50),
  is_staff     boolean      not null default false,
  metadata     jsonb        not null default '{}'::jsonb,
  created_at   timestamptz  not null default now(),
  updated_at   timestamptz  not null default now()
);

create unique index if not exists uq_profiles_username on public.profiles(username);
create index if not exists idx_profiles_metadata on public.profiles using gin(metadata);

-- Auto-create user + profile on auth.users signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  new_user_id text;
  base_username text;
  final_username text;
  suffix int := 0;
begin
  -- Create bridge record
  insert into public.users (auth_user_id)
  values (new.id)
  returning id into new_user_id;

  -- Create profile with collision-safe username
  base_username := coalesce(
    new.raw_user_meta_data ->> 'username',
    split_part(new.email, '@', 1)
  );
  final_username := base_username;

  loop
    begin
      insert into public.profiles (id, username, full_name, display_name)
      values (
        new_user_id,
        final_username,
        coalesce(new.raw_user_meta_data ->> 'full_name', ''),
        coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1))
      );
      exit;
    exception when unique_violation then
      suffix := suffix + 1;
      final_username := base_username || suffix::text;
      if suffix > 100 then
        raise exception 'Could not generate unique username for %', new.email;
      end if;
    end;
  end loop;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Secure function: get current user's email (no view leak)
create or replace function public.get_my_email()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select email from auth.users where id = (select auth.uid());
$$;

grant execute on function public.get_my_email() to authenticated;


-- ************************************************************
-- STAGE 3: ORGANIZATION
-- ************************************************************
-- Learn: Company → Store → Staff hierarchy.
-- Companies own stores. Stores have staff with role-based access.
-- soft-delete (deleted_at) for core business entities.
-- ************************************************************

create table if not exists public.companies (
  id              text primary key default generate_ulid(),
  name            varchar(100)       not null,
  type            public.company_type not null default 'retailer',
  supervisor_id   text references public.users(id) on delete set null,
  description     text               not null default '',
  country_code    varchar(10)        not null default '',
  tax_id          varchar(50)        not null default '',
  url             varchar(255)       not null default '',
  email           varchar(255)       not null default '',
  phone           varchar(50)        not null default '',
  metadata        jsonb              not null default '{}'::jsonb,
  created_at      timestamptz        not null default now(),
  updated_at      timestamptz        not null default now(),
  deleted_at      timestamptz,
  created_by      text references public.users(id) on delete set null,
  updated_by      text references public.users(id) on delete set null
);

create index if not exists idx_companies_supervisor on public.companies(supervisor_id) where supervisor_id is not null;
create index if not exists idx_companies_metadata on public.companies using gin(metadata);
create index if not exists idx_companies_active on public.companies(id) where deleted_at is null;

create table if not exists public.stores (
  id              text primary key default generate_ulid(),
  company_id      text               not null references public.companies(id) on delete restrict,
  name            varchar(100)       not null,
  supervisor_id   text references public.users(id) on delete set null,
  description     text               not null default '',
  phone           varchar(50)        not null default '',
  country_code    varchar(10)        not null default '',
  zip_code        varchar(20)        not null default '',
  state           varchar(50)        not null default '',
  city            varchar(50)        not null default '',
  address         varchar(255)       not null default '',
  is_active       boolean            not null default true,
  metadata        jsonb              not null default '{}'::jsonb,
  created_at      timestamptz        not null default now(),
  updated_at      timestamptz        not null default now(),
  deleted_at      timestamptz,
  created_by      text references public.users(id) on delete set null,
  updated_by      text references public.users(id) on delete set null
);

create index if not exists idx_stores_company on public.stores(company_id);
create index if not exists idx_stores_supervisor on public.stores(supervisor_id) where supervisor_id is not null;
create index if not exists idx_stores_active on public.stores(id) where deleted_at is null and is_active = true;

create table if not exists public.store_staff (
  id         text primary key default generate_ulid(),
  store_id   text   not null references public.stores(id) on delete cascade,
  staff_id   text   not null references public.users(id) on delete cascade,
  roles      text[] not null default array['staff']::text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index if not exists uq_store_staff
  on public.store_staff(store_id, staff_id) where deleted_at is null;
create index if not exists idx_store_staff_staff on public.store_staff(staff_id);


-- ************************************************************
-- STAGE 4: CATALOG
-- ************************************************************
-- Learn: Product modeling for e-commerce.
--   - First-class columns for price/sku (queried constantly)
--   - metadata jsonb for flexible attributes (color, size, etc.)
--   - product_images → Supabase Storage (path reference, not blob)
--   - reviews with rating constraint and one-per-customer uniqueness
--   - parent_id for product variants (variable → children)
--   - pg_trgm + tsvector index for product search
-- ************************************************************

create table if not exists public.products (
  id               text primary key default generate_ulid(),
  author_id        text references public.users(id) on delete set null,
  parent_id        text references public.products(id) on delete set null,
  title            varchar(255)         not null,
  slug             varchar(255)         not null,
  description      text                 not null default '',
  excerpt          text                 not null default '',
  status           public.product_status not null default 'draft',
  type             public.product_type   not null default 'physical',
  sku              varchar(100),
  barcode          varchar(100),
  price            numeric(12,2)        not null default 0,
  compare_at_price numeric(12,2),
  cost_price       numeric(12,2),
  currency         varchar(3)           not null default 'TWD',
  weight_g         integer,
  is_taxable       boolean              not null default true,
  tax_rate         numeric(5,4),
  metadata         jsonb                not null default '{}'::jsonb,
  created_at       timestamptz          not null default now(),
  updated_at       timestamptz          not null default now(),
  deleted_at       timestamptz,
  created_by       text references public.users(id) on delete set null,
  updated_by       text references public.users(id) on delete set null,
  constraint ck_products_price            check (price >= 0),
  constraint ck_products_compare_at_price check (compare_at_price is null or compare_at_price >= 0),
  constraint ck_products_cost_price       check (cost_price is null or cost_price >= 0)
);

create unique index if not exists uq_products_slug on public.products(slug) where deleted_at is null;
create unique index if not exists uq_products_sku  on public.products(sku) where sku is not null and deleted_at is null;
create index if not exists idx_products_author on public.products(author_id);
create index if not exists idx_products_parent on public.products(parent_id);
create index if not exists idx_products_status on public.products(status) where deleted_at is null;
create index if not exists idx_products_type on public.products(type);
create index if not exists idx_products_metadata on public.products using gin(metadata);
create index if not exists idx_products_title_trgm on public.products using gin(title gin_trgm_ops);
create index if not exists idx_products_search on public.products
  using gin(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'')));

-- Product images (reference to Supabase Storage, not binary)
create table if not exists public.product_images (
  id           text primary key default generate_ulid(),
  product_id   text         not null references public.products(id) on delete cascade,
  storage_path text         not null,
  alt_text     varchar(255) not null default '',
  sort_order   smallint     not null default 0,
  is_primary   boolean      not null default false,
  created_at   timestamptz  not null default now(),
  updated_at   timestamptz  not null default now()
);

create index if not exists idx_product_images_product on public.product_images(product_id);
create unique index if not exists uq_product_images_primary
  on public.product_images(product_id) where is_primary = true;

-- Reviews
create table if not exists public.reviews (
  id          text primary key default generate_ulid(),
  product_id  text        not null references public.products(id) on delete cascade,
  customer_id text        not null references public.users(id) on delete cascade,
  rating      smallint    not null,
  title       varchar(255) not null default '',
  body        text        not null default '',
  is_verified boolean     not null default false,
  is_visible  boolean     not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint ck_reviews_rating check (rating between 1 and 5)
);

create index if not exists idx_reviews_product on public.reviews(product_id);
create index if not exists idx_reviews_customer on public.reviews(customer_id);
create unique index if not exists uq_reviews_customer_product
  on public.reviews(product_id, customer_id);


-- ************************************************************
-- STAGE 5: TAXONOMY
-- ************************************************************
-- Learn: Flexible categorization (WordPress-style but simplified).
--   terms = vocabulary entries (e.g. "Electronics", "Red")
--   term_taxonomy = classification context (term + taxonomy type)
--   term_relationships = polymorphic join (object_id → any entity)
-- This pattern supports categories, tags, brands, etc. without
-- creating a separate table for each classification dimension.
-- ************************************************************

create table if not exists public.terms (
  id         text primary key default generate_ulid(),
  name       varchar(200)  not null,
  slug       varchar(255)  not null,
  term_group integer       not null default 0,
  metadata   jsonb         not null default '{}'::jsonb,
  created_at timestamptz   not null default now(),
  updated_at timestamptz   not null default now()
);

create unique index if not exists uq_terms_slug on public.terms(slug);
create index if not exists idx_terms_metadata on public.terms using gin(metadata);

create table if not exists public.term_taxonomy (
  id          text primary key default generate_ulid(),
  term_id     text         not null references public.terms(id) on delete cascade,
  taxonomy    varchar(50)  not null,   -- 'category', 'tag', 'brand', 'color'
  description text         not null default '',
  parent_id   text references public.term_taxonomy(id) on delete set null,
  count       integer      not null default 0,
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now(),
  constraint  ak_term_taxonomy unique (term_id, taxonomy)
);

create index if not exists idx_term_taxonomy_parent on public.term_taxonomy(parent_id);

create table if not exists public.term_relationships (
  object_id        text    not null,   -- polymorphic: product, order, etc.
  term_taxonomy_id text    not null references public.term_taxonomy(id) on delete cascade,
  term_order       integer not null default 0,
  created_at       timestamptz not null default now(),
  primary key (object_id, term_taxonomy_id)
);

create index if not exists idx_term_rel_taxonomy on public.term_relationships(term_taxonomy_id);


-- ************************************************************
-- STAGE 6: INVENTORY
-- ************************************************************
-- Learn: Two-table inventory pattern.
--   stocks = current snapshot (one row per store×product)
--   inventory_movements = audit trail (append-only log)
-- Every stock change creates a movement record for traceability.
-- Movements are append-only — never UPDATE or DELETE.
-- ************************************************************

create table if not exists public.stocks (
  id         text primary key default generate_ulid(),
  store_id   text          not null references public.stores(id) on delete cascade,
  product_id text          not null references public.products(id) on delete restrict,
  quantity   numeric(10,2) not null default 0,
  low_stock_threshold integer,
  created_at timestamptz   not null default now(),
  updated_at timestamptz   not null default now(),
  constraint ck_stocks_quantity  check (quantity >= 0),
  constraint ck_stocks_threshold check (low_stock_threshold is null or low_stock_threshold >= 0)
);

create unique index if not exists uq_stocks_store_product on public.stocks(store_id, product_id);

create table if not exists public.inventory_movements (
  id             text primary key default generate_ulid(),
  store_id       text                 not null references public.stores(id) on delete restrict,
  product_id     text                 not null references public.products(id) on delete restrict,
  quantity_delta  numeric(10,2)       not null,   -- +inbound, -outbound
  reason         public.movement_reason not null default 'manual',
  reference_type varchar(50),
  reference_id   text,
  note           text                 not null default '',
  created_at     timestamptz          not null default now(),
  created_by     text references public.users(id) on delete set null
);

create index if not exists idx_inv_movements_store_product on public.inventory_movements(store_id, product_id);
create index if not exists idx_inv_movements_created on public.inventory_movements(created_at);
create index if not exists idx_inv_movements_ref on public.inventory_movements(reference_type, reference_id)
  where reference_type is not null;


-- ************************************************************
-- STAGE 7: COUPONS & ADDRESSES
-- ************************************************************
-- Learn: Reusable entities that orders depend on.
-- Must be defined BEFORE orders (FK dependency order).
--   coupons = discount rules with validity window
--   addresses = multi-address per customer, one default per label
-- ************************************************************

create table if not exists public.coupons (
  id                    text primary key default generate_ulid(),
  code                  varchar(100)         not null,
  description           text                 not null default '',
  discount_type         public.discount_type not null default 'fixed',
  discount_value        numeric(10,2)        not null default 0,
  min_order_amount      numeric(10,2),
  max_discount          numeric(10,2),
  max_uses              integer,
  max_uses_per_customer integer,
  used_count            integer              not null default 0,
  starts_at             timestamptz,
  expires_at            timestamptz,
  is_active             boolean              not null default true,
  metadata              jsonb                not null default '{}'::jsonb,
  created_at            timestamptz          not null default now(),
  updated_at            timestamptz          not null default now(),
  deleted_at            timestamptz,
  created_by            text references public.users(id) on delete set null,
  updated_by            text references public.users(id) on delete set null,
  constraint ck_coupons_discount_value check (discount_value >= 0),
  constraint ck_coupons_used_count     check (used_count >= 0),
  constraint ck_coupons_dates          check (expires_at is null or starts_at is null or expires_at > starts_at)
);

create unique index if not exists uq_coupons_code on public.coupons(code) where deleted_at is null;

create table if not exists public.addresses (
  id           text primary key default generate_ulid(),
  customer_id  text                 not null references public.users(id) on delete cascade,
  label        public.address_label not null default 'home',
  recipient    varchar(200)         not null default '',
  phone        varchar(50)          not null default '',
  country_code varchar(10)          not null default '',
  state        varchar(50)          not null default '',
  city         varchar(50)          not null default '',
  zip_code     varchar(20)          not null default '',
  address_1    varchar(255)         not null default '',
  address_2    varchar(255)         not null default '',
  is_default   boolean              not null default false,
  metadata     jsonb                not null default '{}'::jsonb,
  created_at   timestamptz          not null default now(),
  updated_at   timestamptz          not null default now()
);

create index if not exists idx_addresses_customer on public.addresses(customer_id);
create unique index if not exists uq_addresses_default
  on public.addresses(customer_id, label) where is_default = true;


-- ************************************************************
-- STAGE 8: COMMERCE
-- ************************************************************
-- Learn: The transactional core of e-commerce.
--   orders → order_items (line items with product snapshots)
--   order_coupons (junction: which coupons applied)
--   payments (lifecycle: pending → paid → refunded)
--   point_rewards (ledger: +earn / -spend, balance via view)
--
-- Key patterns:
--   - order_items snapshot product_title/sku at purchase time
--   - payments.refund_amount <= amount (enforced by CHECK)
--   - point_rewards is append-only; balance computed, never stored
-- ************************************************************

create table if not exists public.orders (
  id                  text primary key default generate_ulid(),
  customer_id         text                not null references public.users(id) on delete restrict,
  parent_id           text references public.orders(id) on delete set null,
  status              public.order_status not null default 'pending',
  num_items_sold      integer             not null default 0,
  subtotal            numeric(12,2)       not null default 0,
  tax_total           numeric(12,2)       not null default 0,
  shipping_total      numeric(12,2)       not null default 0,
  discount_total      numeric(12,2)       not null default 0,
  total               numeric(12,2)       not null default 0,
  currency            varchar(3)          not null default 'TWD',
  shipping_address_id text references public.addresses(id) on delete set null,
  billing_address_id  text references public.addresses(id) on delete set null,
  returning_customer  boolean,
  note                text                not null default '',
  metadata            jsonb               not null default '{}'::jsonb,
  created_at          timestamptz         not null default now(),
  updated_at          timestamptz         not null default now(),
  deleted_at          timestamptz,
  created_by          text references public.users(id) on delete set null,
  updated_by          text references public.users(id) on delete set null,
  constraint ck_orders_num_items check (num_items_sold >= 0),
  constraint ck_orders_subtotal  check (subtotal >= 0),
  constraint ck_orders_tax       check (tax_total >= 0),
  constraint ck_orders_shipping  check (shipping_total >= 0),
  constraint ck_orders_discount  check (discount_total >= 0),
  constraint ck_orders_total     check (total >= 0)
);

create index if not exists idx_orders_customer on public.orders(customer_id);
create index if not exists idx_orders_parent on public.orders(parent_id) where parent_id is not null;
create index if not exists idx_orders_status on public.orders(status) where deleted_at is null;
create index if not exists idx_orders_created on public.orders(created_at);
create index if not exists idx_orders_shipping_addr on public.orders(shipping_address_id) where shipping_address_id is not null;
create index if not exists idx_orders_billing_addr on public.orders(billing_address_id) where billing_address_id is not null;
create index if not exists idx_orders_metadata on public.orders using gin(metadata);

create table if not exists public.order_items (
  id                  text primary key default generate_ulid(),
  order_id            text          not null references public.orders(id) on delete cascade,
  product_id          text          not null references public.products(id) on delete restrict,
  variation_id        text references public.products(id) on delete set null,
  product_title       varchar(255)  not null default '',   -- snapshot at purchase
  sku                 varchar(100),                        -- snapshot at purchase
  quantity            numeric(10,2) not null default 1,
  unit_price          numeric(12,2) not null default 0,
  gross_revenue       numeric(12,2) not null default 0,
  net_revenue         numeric(12,2) not null default 0,
  coupon_amount       numeric(12,2) not null default 0,
  tax_amount          numeric(12,2) not null default 0,
  shipping_amount     numeric(12,2) not null default 0,
  shipping_tax_amount numeric(12,2) not null default 0,
  created_at          timestamptz   not null default now(),
  updated_at          timestamptz   not null default now(),
  constraint ck_order_items_quantity   check (quantity > 0),
  constraint ck_order_items_unit_price check (unit_price >= 0)
);

create index if not exists idx_order_items_order on public.order_items(order_id);
create index if not exists idx_order_items_product on public.order_items(product_id);
create index if not exists idx_order_items_variation on public.order_items(variation_id) where variation_id is not null;

create table if not exists public.order_coupons (
  order_id         text          not null references public.orders(id) on delete cascade,
  coupon_id        text          not null references public.coupons(id) on delete restrict,
  discount_amount  numeric(12,2) not null default 0,
  created_at       timestamptz   not null default now(),
  primary key (order_id, coupon_id)
);

create index if not exists idx_order_coupons_coupon on public.order_coupons(coupon_id);

create table if not exists public.payments (
  id                text primary key default generate_ulid(),
  order_id          text                  not null references public.orders(id) on delete restrict,
  customer_id       text                  not null references public.users(id) on delete restrict,
  amount            numeric(12,2)         not null default 0,
  currency          varchar(3)            not null default 'TWD',
  method            public.payment_method not null,
  provider          varchar(50)           not null default '',
  provider_tx_id    varchar(255),
  status            public.payment_status not null default 'pending',
  paid_at           timestamptz,
  refunded_at       timestamptz,
  refund_amount     numeric(12,2)         not null default 0,
  failure_reason    text,
  metadata          jsonb                 not null default '{}'::jsonb,
  created_at        timestamptz           not null default now(),
  updated_at        timestamptz           not null default now(),
  created_by        text references public.users(id) on delete set null,
  updated_by        text references public.users(id) on delete set null,
  constraint ck_payments_amount        check (amount >= 0),
  constraint ck_payments_refund_amount check (refund_amount >= 0 and refund_amount <= amount)
);

create index if not exists idx_payments_order on public.payments(order_id);
create index if not exists idx_payments_customer on public.payments(customer_id);
create index if not exists idx_payments_status on public.payments(status);
create index if not exists idx_payments_provider_tx
  on public.payments(provider_tx_id) where provider_tx_id is not null;

-- Point rewards (append-only ledger)
create table if not exists public.point_rewards (
  id           text primary key default generate_ulid(),
  customer_id  text   not null references public.users(id) on delete restrict,
  order_id     text references public.orders(id) on delete restrict,
  points       bigint not null,   -- +earn, -spend
  description  text   not null default '',
  created_at   timestamptz not null default now()
);

create index if not exists idx_point_rewards_customer on public.point_rewards(customer_id);
create index if not exists idx_point_rewards_order on public.point_rewards(order_id) where order_id is not null;

-- Computed balance (always accurate, no desync)
create or replace view public.point_balances
  with (security_invoker = true)
  as
  select customer_id, coalesce(sum(points), 0) as balance
  from public.point_rewards
  group by customer_id;


-- ************************************************************
-- STAGE 9: SECURITY (RLS + Policies + GRANTs)
-- ************************************************************
-- Learn: Supabase RLS best practices.
--   1. Helper functions (no inline JOIN/EXISTS in policies)
--   2. (SELECT auth.uid()) not auth.uid() (initPlan optimization)
--   3. Every table: enable RLS + policies + GRANTs
--   4. service_role policy on every table (for ETL/cron/webhooks)
--   5. GRANT EXECUTE on helper functions
-- ************************************************************

-- --- RLS Helper Functions ---

create or replace function public.is_staff()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    (select is_staff from public.profiles where id = public.get_current_user_id()),
    false
  );
$$;

grant execute on function public.is_staff() to authenticated;

create or replace function public.is_store_staff(p_store_id text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.store_staff
    where store_id = p_store_id
      and staff_id = public.get_current_user_id()
      and deleted_at is null
  );
$$;

grant execute on function public.is_store_staff(text) to authenticated;

-- Helper: does the current user own this order?
create or replace function public.is_order_owner(p_order_id text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.orders
    where id = p_order_id
      and customer_id = public.get_current_user_id()
  );
$$;

grant execute on function public.is_order_owner(text) to authenticated;

-- Helper: is the product publicly visible?
create or replace function public.is_product_visible(p_product_id text)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.products
    where id = p_product_id
      and status = 'publish'
      and deleted_at is null
  );
$$;

grant execute on function public.is_product_visible(text) to authenticated, anon;

-- --- Enable RLS on ALL tables ---

do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'users', 'profiles', 'companies', 'stores', 'store_staff',
    'products', 'product_images', 'reviews', 'stocks',
    'inventory_movements', 'coupons', 'addresses',
    'orders', 'order_items', 'order_coupons',
    'payments', 'point_rewards',
    'terms', 'term_taxonomy', 'term_relationships'
  ]
  loop
    execute format('alter table public.%I enable row level security;', tbl);
  end loop;
end;
$$;

-- --- Policies ---

-- Users: read all, no direct writes (managed by trigger)
create policy "users_select"       on public.users for select to authenticated using (true);
create policy "users_service_role" on public.users for all to service_role using (true) with check (true);

-- Profiles: read all, update own
create policy "profiles_select"       on public.profiles for select to authenticated using (true);
create policy "profiles_update_own"   on public.profiles for update to authenticated using (id = public.get_current_user_id());
create policy "profiles_service_role" on public.profiles for all to service_role using (true) with check (true);

-- Products: published = public, draft = author/staff
create policy "products_select" on public.products for select to authenticated, anon
  using (
    (status = 'publish' and deleted_at is null)
    or author_id = public.get_current_user_id()
    or public.is_staff()
  );
create policy "products_insert_staff" on public.products for insert to authenticated
  with check (public.is_staff());
create policy "products_update_staff" on public.products for update to authenticated
  using (public.is_staff());
create policy "products_delete_staff" on public.products for delete to authenticated
  using (public.is_staff());
create policy "products_service_role" on public.products for all to service_role
  using (true) with check (true);

-- Product images: follow product visibility
create policy "product_images_select" on public.product_images for select to authenticated, anon
  using (public.is_product_visible(product_id) or public.is_staff());
create policy "product_images_insert_staff" on public.product_images for insert to authenticated
  with check (public.is_staff());
create policy "product_images_update_staff" on public.product_images for update to authenticated
  using (public.is_staff());
create policy "product_images_delete_staff" on public.product_images for delete to authenticated
  using (public.is_staff());
create policy "product_images_service_role" on public.product_images for all to service_role
  using (true) with check (true);

-- Reviews: visible = public, write own
create policy "reviews_select" on public.reviews for select to authenticated, anon
  using (is_visible = true or customer_id = public.get_current_user_id() or public.is_staff());
create policy "reviews_insert_own" on public.reviews for insert to authenticated
  with check (customer_id = public.get_current_user_id());
create policy "reviews_update_own" on public.reviews for update to authenticated
  using (customer_id = public.get_current_user_id());
create policy "reviews_delete_staff" on public.reviews for delete to authenticated
  using (public.is_staff());
create policy "reviews_service_role" on public.reviews for all to service_role
  using (true) with check (true);

-- Orders: customer sees own, staff sees all
create policy "orders_select" on public.orders for select to authenticated
  using (customer_id = public.get_current_user_id() or public.is_staff());
create policy "orders_insert" on public.orders for insert to authenticated
  with check (customer_id = public.get_current_user_id());
create policy "orders_update_staff" on public.orders for update to authenticated
  using (public.is_staff());
create policy "orders_service_role" on public.orders for all to service_role
  using (true) with check (true);

-- Order items: inherit from parent order (via helper, no inline JOIN)
create policy "order_items_select" on public.order_items for select to authenticated
  using (public.is_order_owner(order_id) or public.is_staff());
create policy "order_items_insert_staff" on public.order_items for insert to authenticated
  with check (public.is_order_owner(order_id) or public.is_staff());
create policy "order_items_update_staff" on public.order_items for update to authenticated
  using (public.is_staff());
create policy "order_items_delete_staff" on public.order_items for delete to authenticated
  using (public.is_staff());
create policy "order_items_service_role" on public.order_items for all to service_role
  using (true) with check (true);

-- Order coupons: inherit from parent order
create policy "order_coupons_select" on public.order_coupons for select to authenticated
  using (public.is_order_owner(order_id) or public.is_staff());
create policy "order_coupons_insert_staff" on public.order_coupons for insert to authenticated
  with check (public.is_staff());
create policy "order_coupons_update_staff" on public.order_coupons for update to authenticated
  using (public.is_staff());
create policy "order_coupons_delete_staff" on public.order_coupons for delete to authenticated
  using (public.is_staff());
create policy "order_coupons_service_role" on public.order_coupons for all to service_role
  using (true) with check (true);

-- Addresses: customer manages own
create policy "addresses_select" on public.addresses for select to authenticated
  using (customer_id = public.get_current_user_id() or public.is_staff());
create policy "addresses_insert_own" on public.addresses for insert to authenticated
  with check (customer_id = public.get_current_user_id());
create policy "addresses_update_own" on public.addresses for update to authenticated
  using (customer_id = public.get_current_user_id());
create policy "addresses_delete_own" on public.addresses for delete to authenticated
  using (customer_id = public.get_current_user_id());
create policy "addresses_service_role" on public.addresses for all to service_role
  using (true) with check (true);

-- Payments: customer views own, staff manages
create policy "payments_select" on public.payments for select to authenticated
  using (customer_id = public.get_current_user_id() or public.is_staff());
create policy "payments_insert" on public.payments for insert to authenticated
  with check (customer_id = public.get_current_user_id() or public.is_staff());
create policy "payments_update_staff" on public.payments for update to authenticated
  using (public.is_staff());
create policy "payments_service_role" on public.payments for all to service_role
  using (true) with check (true);

-- Point rewards: customer views own
create policy "point_rewards_select" on public.point_rewards for select to authenticated
  using (customer_id = public.get_current_user_id() or public.is_staff());
create policy "point_rewards_insert_staff" on public.point_rewards for insert to authenticated
  with check (public.is_staff());
create policy "point_rewards_service_role" on public.point_rewards for all to service_role
  using (true) with check (true);

-- Stores: public read
create policy "stores_select" on public.stores for select to authenticated, anon using (true);

-- Companies: staff only
create policy "companies_select" on public.companies for select to authenticated
  using (public.is_staff());

-- Stocks / inventory: staff + store-level staff
create policy "stocks_select" on public.stocks for select to authenticated
  using (public.is_staff() or public.is_store_staff(store_id));
create policy "inventory_movements_select" on public.inventory_movements for select to authenticated
  using (public.is_staff() or public.is_store_staff(store_id));

-- Coupons: active & valid = public, all = staff
create policy "coupons_select" on public.coupons for select to authenticated, anon
  using (
    (is_active = true and deleted_at is null
     and (starts_at is null or starts_at <= now())
     and (expires_at is null or expires_at > now()))
    or public.is_staff()
  );

-- Store staff: own record or global staff
create policy "store_staff_select" on public.store_staff for select to authenticated
  using (staff_id = public.get_current_user_id() or public.is_staff());

-- Terms / taxonomy: public read
create policy "terms_select" on public.terms for select to authenticated, anon using (true);
create policy "term_taxonomy_select" on public.term_taxonomy for select to authenticated, anon using (true);
create policy "term_relationships_select" on public.term_relationships for select to authenticated, anon using (true);

-- Staff write policies (blanket for admin-managed tables)
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'companies', 'stores', 'stocks', 'store_staff',
    'inventory_movements', 'coupons',
    'terms', 'term_taxonomy', 'term_relationships'
  ]
  loop
    execute format('
      create policy "%1$s_insert_staff" on public.%1$s for insert to authenticated
        with check (public.is_staff());
      create policy "%1$s_update_staff" on public.%1$s for update to authenticated
        using (public.is_staff());
      create policy "%1$s_delete_staff" on public.%1$s for delete to authenticated
        using (public.is_staff());
      create policy "%1$s_service_role" on public.%1$s for all to service_role
        using (true) with check (true);
    ', tbl);
  end loop;
end;
$$;

-- --- GRANTs ---

do $$
declare
  tbl text;
begin
  -- All tables: authenticated can SELECT; service_role can ALL
  foreach tbl in array array[
    'users', 'profiles', 'companies', 'stores', 'store_staff',
    'products', 'product_images', 'reviews', 'stocks',
    'inventory_movements', 'coupons', 'addresses',
    'orders', 'order_items', 'order_coupons',
    'payments', 'point_rewards',
    'terms', 'term_taxonomy', 'term_relationships'
  ]
  loop
    execute format('grant select on public.%I to authenticated;', tbl);
    execute format('grant insert, update, delete on public.%I to authenticated;', tbl);
    execute format('grant all on public.%I to service_role;', tbl);
  end loop;

  -- Public-readable tables: anon can SELECT
  foreach tbl in array array[
    'products', 'product_images', 'stores',
    'terms', 'term_taxonomy', 'term_relationships',
    'coupons', 'reviews'
  ]
  loop
    execute format('grant select on public.%I to anon;', tbl);
  end loop;
end;
$$;


-- ************************************************************
-- STAGE 10: AUTOMATION
-- ************************************************************
-- Learn: Triggers, Realtime subscriptions, Storage buckets.
--   - moddatetime: Supabase-native updated_at trigger
--   - handle_audit_fields: auto-fill created_by/updated_by
--   - Realtime: only on tables that benefit from live updates
--   - Storage: bucket for product images with RLS
-- ************************************************************

-- updated_at triggers (moddatetime extension)
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'users', 'profiles', 'companies', 'stores', 'store_staff',
    'products', 'product_images', 'stocks', 'coupons',
    'orders', 'order_items', 'addresses', 'payments', 'reviews',
    'terms', 'term_taxonomy'
  ]
  loop
    execute format('
      drop trigger if exists trg_%1$s_updated_at on public.%1$s;
      create trigger trg_%1$s_updated_at
        before update on public.%1$s
        for each row execute function moddatetime(updated_at);
    ', tbl);
  end loop;
end;
$$;

-- Audit fields triggers (created_by / updated_by)
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'companies', 'stores', 'products', 'coupons', 'orders', 'payments'
  ]
  loop
    execute format('
      drop trigger if exists trg_%1$s_audit on public.%1$s;
      create trigger trg_%1$s_audit
        before insert or update on public.%1$s
        for each row execute function public.handle_audit_fields();
    ', tbl);
  end loop;
end;
$$;

-- Supabase Realtime (enable via Dashboard or SQL)
-- Only on tables that benefit from live updates:
--
-- alter publication supabase_realtime add table public.orders;
-- alter publication supabase_realtime add table public.stocks;
-- alter publication supabase_realtime add table public.payments;
-- alter publication supabase_realtime add table public.reviews;

-- Supabase Storage bucket for product images
-- Run via Dashboard or:
--
-- insert into storage.buckets (id, name, public)
-- values ('product-images', 'product-images', true);
--
-- create policy "product_images_public_read"
--   on storage.objects for select
--   using (bucket_id = 'product-images');
--
-- create policy "product_images_staff_upload"
--   on storage.objects for insert to authenticated
--   with check (bucket_id = 'product-images' and public.is_staff());
--
-- create policy "product_images_staff_delete"
--   on storage.objects for delete to authenticated
--   using (bucket_id = 'product-images' and public.is_staff());
