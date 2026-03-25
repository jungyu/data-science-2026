-- ============================================================
-- Supabase-Native E-Commerce Schema  v3.0
-- Stage-by-Stage Learning Edition
-- ============================================================
--
-- Conventions (aligned with project skill guidelines):
--   - PK: TEXT DEFAULT public.generate_ulid()  (not BIGINT, not UUID)
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
--   Stage 1: Foundation (types, helpers)  — extensions/ULID 在 001_extensions.sql
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

-- NOTE: schema, extensions, generate_ulid() 已移至 001_extensions.sql

-- Custom enum types
do $$ begin create type shop.company_type    as enum ('retailer','wholesaler','manufacturer','distributor');              exception when duplicate_object then null; end $$;
do $$ begin create type shop.product_status  as enum ('draft','publish','archived','trash');                              exception when duplicate_object then null; end $$;
do $$ begin create type shop.product_type    as enum ('physical','digital','virtual','grouped','variable');               exception when duplicate_object then null; end $$;
do $$ begin create type shop.order_status    as enum ('pending','confirmed','processing','shipped','delivered','cancelled','refunded'); exception when duplicate_object then null; end $$;
do $$ begin create type shop.payment_status  as enum ('pending','processing','paid','failed','refunded','partially_refunded','cancelled'); exception when duplicate_object then null; end $$;
do $$ begin create type shop.payment_method  as enum ('credit_card','debit_card','line_pay','apple_pay','google_pay','bank_transfer','cash_on_delivery','points'); exception when duplicate_object then null; end $$;
do $$ begin create type shop.discount_type   as enum ('fixed','percentage','free_shipping');                              exception when duplicate_object then null; end $$;
do $$ begin create type shop.movement_reason as enum ('sale','return','restock','adjustment','manual','transfer');        exception when duplicate_object then null; end $$;
do $$ begin create type shop.address_label   as enum ('home','office','shipping','billing','other');                      exception when duplicate_object then null; end $$;

-- Audit fields trigger (auto-fill created_by / updated_by)
create or replace function shop.handle_audit_fields()
returns trigger
language plpgsql
security definer
set search_path = shop
as $$
begin
  if tg_op = 'INSERT' then
    new.created_by = coalesce(new.created_by, shop.get_current_user_id());
    new.updated_by = coalesce(new.updated_by, shop.get_current_user_id());
  elsif tg_op = 'UPDATE' then
    new.updated_by = coalesce(shop.get_current_user_id(), new.updated_by);
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

create table if not exists shop.users (
  id            text primary key default public.generate_ulid(),
  auth_user_id  uuid unique not null references auth.users(id) on delete cascade,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists idx_users_auth on shop.users(auth_user_id);

-- Bridge helper: auth UUID → ULID user ID (cached per statement)
create or replace function shop.get_current_user_id()
returns text
language sql
stable
security definer
set search_path = shop
as $$
  select id from shop.users where auth_user_id = (select auth.uid()) limit 1;
$$;

grant execute on function shop.get_current_user_id() to authenticated;

-- Profiles (extended user data)
create table if not exists shop.profiles (
  id           text primary key references shop.users(id) on delete cascade,
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

create unique index if not exists uq_profiles_username on shop.profiles(username);
create index if not exists idx_profiles_metadata on shop.profiles using gin(metadata);

-- Auto-create user + profile on auth.users signup
create or replace function shop.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = shop
as $$
declare
  new_user_id text;
  base_username text;
  final_username text;
  suffix int := 0;
begin
  -- Create bridge record
  insert into shop.users (auth_user_id)
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
      insert into shop.profiles (id, username, full_name, display_name)
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
  for each row execute function shop.handle_new_user();

-- Secure function: get current user's email (no view leak)
create or replace function shop.get_my_email()
returns text
language sql
stable
security definer
set search_path = shop
as $$
  select email from auth.users where id = (select auth.uid());
$$;

grant execute on function shop.get_my_email() to authenticated;


-- ************************************************************
-- STAGE 3: ORGANIZATION
-- ************************************************************
-- Learn: Company → Store → Staff hierarchy.
-- Companies own stores. Stores have staff with role-based access.
-- soft-delete (deleted_at) for core business entities.
-- ************************************************************

create table if not exists shop.companies (
  id              text primary key default public.generate_ulid(),
  name            varchar(100)       not null,
  type            shop.company_type not null default 'retailer',
  supervisor_id   text references shop.users(id) on delete set null,
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
  created_by      text references shop.users(id) on delete set null,
  updated_by      text references shop.users(id) on delete set null
);

create index if not exists idx_companies_supervisor on shop.companies(supervisor_id) where supervisor_id is not null;
create index if not exists idx_companies_metadata on shop.companies using gin(metadata);
create index if not exists idx_companies_active on shop.companies(id) where deleted_at is null;

create table if not exists shop.stores (
  id              text primary key default public.generate_ulid(),
  company_id      text               not null references shop.companies(id) on delete restrict,
  name            varchar(100)       not null,
  supervisor_id   text references shop.users(id) on delete set null,
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
  created_by      text references shop.users(id) on delete set null,
  updated_by      text references shop.users(id) on delete set null
);

create index if not exists idx_stores_company on shop.stores(company_id);
create index if not exists idx_stores_supervisor on shop.stores(supervisor_id) where supervisor_id is not null;
create index if not exists idx_stores_active on shop.stores(id) where deleted_at is null and is_active = true;

create table if not exists shop.store_staff (
  id         text primary key default public.generate_ulid(),
  store_id   text   not null references shop.stores(id) on delete cascade,
  staff_id   text   not null references shop.users(id) on delete cascade,
  roles      text[] not null default array['staff']::text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create unique index if not exists uq_store_staff
  on shop.store_staff(store_id, staff_id) where deleted_at is null;
create index if not exists idx_store_staff_staff on shop.store_staff(staff_id);


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

create table if not exists shop.products (
  id               text primary key default public.generate_ulid(),
  author_id        text references shop.users(id) on delete set null,
  parent_id        text references shop.products(id) on delete set null,
  title            varchar(255)         not null,
  slug             varchar(255)         not null,
  description      text                 not null default '',
  excerpt          text                 not null default '',
  status           shop.product_status not null default 'draft',
  type             shop.product_type   not null default 'physical',
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
  created_by       text references shop.users(id) on delete set null,
  updated_by       text references shop.users(id) on delete set null,
  constraint ck_products_price            check (price >= 0),
  constraint ck_products_compare_at_price check (compare_at_price is null or compare_at_price >= 0),
  constraint ck_products_cost_price       check (cost_price is null or cost_price >= 0)
);

create unique index if not exists uq_products_slug on shop.products(slug) where deleted_at is null;
create unique index if not exists uq_products_sku  on shop.products(sku) where sku is not null and deleted_at is null;
create index if not exists idx_products_author on shop.products(author_id);
create index if not exists idx_products_parent on shop.products(parent_id);
create index if not exists idx_products_status on shop.products(status) where deleted_at is null;
create index if not exists idx_products_type on shop.products(type);
create index if not exists idx_products_metadata on shop.products using gin(metadata);
create index if not exists idx_products_title_trgm on shop.products using gin(title gin_trgm_ops);
create index if not exists idx_products_search on shop.products
  using gin(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'')));

-- Product images (reference to Supabase Storage, not binary)
create table if not exists shop.product_images (
  id           text primary key default public.generate_ulid(),
  product_id   text         not null references shop.products(id) on delete cascade,
  storage_path text         not null,
  alt_text     varchar(255) not null default '',
  sort_order   smallint     not null default 0,
  is_primary   boolean      not null default false,
  created_at   timestamptz  not null default now(),
  updated_at   timestamptz  not null default now()
);

create index if not exists idx_product_images_product on shop.product_images(product_id);
create unique index if not exists uq_product_images_primary
  on shop.product_images(product_id) where is_primary = true;

-- Reviews
create table if not exists shop.reviews (
  id          text primary key default public.generate_ulid(),
  product_id  text        not null references shop.products(id) on delete cascade,
  customer_id text        not null references shop.users(id) on delete cascade,
  rating      smallint    not null,
  title       varchar(255) not null default '',
  body        text        not null default '',
  is_verified boolean     not null default false,
  is_visible  boolean     not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint ck_reviews_rating check (rating between 1 and 5)
);

create index if not exists idx_reviews_product on shop.reviews(product_id);
create index if not exists idx_reviews_customer on shop.reviews(customer_id);
create unique index if not exists uq_reviews_customer_product
  on shop.reviews(product_id, customer_id);


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

create table if not exists shop.terms (
  id         text primary key default public.generate_ulid(),
  name       varchar(200)  not null,
  slug       varchar(255)  not null,
  term_group integer       not null default 0,
  metadata   jsonb         not null default '{}'::jsonb,
  created_at timestamptz   not null default now(),
  updated_at timestamptz   not null default now()
);

create unique index if not exists uq_terms_slug on shop.terms(slug);
create index if not exists idx_terms_metadata on shop.terms using gin(metadata);

create table if not exists shop.term_taxonomy (
  id          text primary key default public.generate_ulid(),
  term_id     text         not null references shop.terms(id) on delete cascade,
  taxonomy    varchar(50)  not null,   -- 'category', 'tag', 'brand', 'color'
  description text         not null default '',
  parent_id   text references shop.term_taxonomy(id) on delete set null,
  count       integer      not null default 0,
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now(),
  constraint  ak_term_taxonomy unique (term_id, taxonomy)
);

create index if not exists idx_term_taxonomy_parent on shop.term_taxonomy(parent_id);

create table if not exists shop.term_relationships (
  object_id        text    not null,   -- polymorphic: product, order, etc.
  term_taxonomy_id text    not null references shop.term_taxonomy(id) on delete cascade,
  term_order       integer not null default 0,
  created_at       timestamptz not null default now(),
  primary key (object_id, term_taxonomy_id)
);

create index if not exists idx_term_rel_taxonomy on shop.term_relationships(term_taxonomy_id);


-- ************************************************************
-- STAGE 6: INVENTORY
-- ************************************************************
-- Learn: Two-table inventory pattern.
--   stocks = current snapshot (one row per store×product)
--   inventory_movements = audit trail (append-only log)
-- Every stock change creates a movement record for traceability.
-- Movements are append-only — never UPDATE or DELETE.
-- ************************************************************

create table if not exists shop.stocks (
  id         text primary key default public.generate_ulid(),
  store_id   text          not null references shop.stores(id) on delete cascade,
  product_id text          not null references shop.products(id) on delete restrict,
  quantity   numeric(10,2) not null default 0,
  low_stock_threshold integer,
  created_at timestamptz   not null default now(),
  updated_at timestamptz   not null default now(),
  constraint ck_stocks_quantity  check (quantity >= 0),
  constraint ck_stocks_threshold check (low_stock_threshold is null or low_stock_threshold >= 0)
);

create unique index if not exists uq_stocks_store_product on shop.stocks(store_id, product_id);

create table if not exists shop.inventory_movements (
  id             text primary key default public.generate_ulid(),
  store_id       text                 not null references shop.stores(id) on delete restrict,
  product_id     text                 not null references shop.products(id) on delete restrict,
  quantity_delta  numeric(10,2)       not null,   -- +inbound, -outbound
  reason         shop.movement_reason not null default 'manual',
  reference_type varchar(50),
  reference_id   text,
  note           text                 not null default '',
  created_at     timestamptz          not null default now(),
  created_by     text references shop.users(id) on delete set null
);

create index if not exists idx_inv_movements_store_product on shop.inventory_movements(store_id, product_id);
create index if not exists idx_inv_movements_created on shop.inventory_movements(created_at);
create index if not exists idx_inv_movements_ref on shop.inventory_movements(reference_type, reference_id)
  where reference_type is not null;


-- ************************************************************
-- STAGE 7: COUPONS & ADDRESSES
-- ************************************************************
-- Learn: Reusable entities that orders depend on.
-- Must be defined BEFORE orders (FK dependency order).
--   coupons = discount rules with validity window
--   addresses = multi-address per customer, one default per label
-- ************************************************************

create table if not exists shop.coupons (
  id                    text primary key default public.generate_ulid(),
  code                  varchar(100)         not null,
  description           text                 not null default '',
  discount_type         shop.discount_type not null default 'fixed',
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
  created_by            text references shop.users(id) on delete set null,
  updated_by            text references shop.users(id) on delete set null,
  constraint ck_coupons_discount_value check (discount_value >= 0),
  constraint ck_coupons_used_count     check (used_count >= 0),
  constraint ck_coupons_dates          check (expires_at is null or starts_at is null or expires_at > starts_at)
);

create unique index if not exists uq_coupons_code on shop.coupons(code) where deleted_at is null;

create table if not exists shop.addresses (
  id           text primary key default public.generate_ulid(),
  customer_id  text                 not null references shop.users(id) on delete cascade,
  label        shop.address_label not null default 'home',
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

create index if not exists idx_addresses_customer on shop.addresses(customer_id);
create unique index if not exists uq_addresses_default
  on shop.addresses(customer_id, label) where is_default = true;


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

create table if not exists shop.orders (
  id                  text primary key default public.generate_ulid(),
  customer_id         text                not null references shop.users(id) on delete restrict,
  parent_id           text references shop.orders(id) on delete set null,
  status              shop.order_status not null default 'pending',
  num_items_sold      integer             not null default 0,
  subtotal            numeric(12,2)       not null default 0,
  tax_total           numeric(12,2)       not null default 0,
  shipping_total      numeric(12,2)       not null default 0,
  discount_total      numeric(12,2)       not null default 0,
  total               numeric(12,2)       not null default 0,
  currency            varchar(3)          not null default 'TWD',
  shipping_address_id text references shop.addresses(id) on delete set null,
  billing_address_id  text references shop.addresses(id) on delete set null,
  returning_customer  boolean,
  note                text                not null default '',
  metadata            jsonb               not null default '{}'::jsonb,
  created_at          timestamptz         not null default now(),
  updated_at          timestamptz         not null default now(),
  deleted_at          timestamptz,
  created_by          text references shop.users(id) on delete set null,
  updated_by          text references shop.users(id) on delete set null,
  constraint ck_orders_num_items check (num_items_sold >= 0),
  constraint ck_orders_subtotal  check (subtotal >= 0),
  constraint ck_orders_tax       check (tax_total >= 0),
  constraint ck_orders_shipping  check (shipping_total >= 0),
  constraint ck_orders_discount  check (discount_total >= 0),
  constraint ck_orders_total     check (total >= 0)
);

create index if not exists idx_orders_customer on shop.orders(customer_id);
create index if not exists idx_orders_parent on shop.orders(parent_id) where parent_id is not null;
create index if not exists idx_orders_status on shop.orders(status) where deleted_at is null;
create index if not exists idx_orders_created on shop.orders(created_at);
create index if not exists idx_orders_shipping_addr on shop.orders(shipping_address_id) where shipping_address_id is not null;
create index if not exists idx_orders_billing_addr on shop.orders(billing_address_id) where billing_address_id is not null;
create index if not exists idx_orders_metadata on shop.orders using gin(metadata);

create table if not exists shop.order_items (
  id                  text primary key default public.generate_ulid(),
  order_id            text          not null references shop.orders(id) on delete cascade,
  product_id          text          not null references shop.products(id) on delete restrict,
  variation_id        text references shop.products(id) on delete set null,
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

create index if not exists idx_order_items_order on shop.order_items(order_id);
create index if not exists idx_order_items_product on shop.order_items(product_id);
create index if not exists idx_order_items_variation on shop.order_items(variation_id) where variation_id is not null;

create table if not exists shop.order_coupons (
  order_id         text          not null references shop.orders(id) on delete cascade,
  coupon_id        text          not null references shop.coupons(id) on delete restrict,
  discount_amount  numeric(12,2) not null default 0,
  created_at       timestamptz   not null default now(),
  primary key (order_id, coupon_id)
);

create index if not exists idx_order_coupons_coupon on shop.order_coupons(coupon_id);

create table if not exists shop.payments (
  id                text primary key default public.generate_ulid(),
  order_id          text                  not null references shop.orders(id) on delete restrict,
  customer_id       text                  not null references shop.users(id) on delete restrict,
  amount            numeric(12,2)         not null default 0,
  currency          varchar(3)            not null default 'TWD',
  method            shop.payment_method not null,
  provider          varchar(50)           not null default '',
  provider_tx_id    varchar(255),
  status            shop.payment_status not null default 'pending',
  paid_at           timestamptz,
  refunded_at       timestamptz,
  refund_amount     numeric(12,2)         not null default 0,
  failure_reason    text,
  metadata          jsonb                 not null default '{}'::jsonb,
  created_at        timestamptz           not null default now(),
  updated_at        timestamptz           not null default now(),
  created_by        text references shop.users(id) on delete set null,
  updated_by        text references shop.users(id) on delete set null,
  constraint ck_payments_amount        check (amount >= 0),
  constraint ck_payments_refund_amount check (refund_amount >= 0 and refund_amount <= amount)
);

create index if not exists idx_payments_order on shop.payments(order_id);
create index if not exists idx_payments_customer on shop.payments(customer_id);
create index if not exists idx_payments_status on shop.payments(status);
create index if not exists idx_payments_provider_tx
  on shop.payments(provider_tx_id) where provider_tx_id is not null;

-- Point rewards (append-only ledger)
create table if not exists shop.point_rewards (
  id           text primary key default public.generate_ulid(),
  customer_id  text   not null references shop.users(id) on delete restrict,
  order_id     text references shop.orders(id) on delete restrict,
  points       bigint not null,   -- +earn, -spend
  description  text   not null default '',
  created_at   timestamptz not null default now()
);

create index if not exists idx_point_rewards_customer on shop.point_rewards(customer_id);
create index if not exists idx_point_rewards_order on shop.point_rewards(order_id) where order_id is not null;

-- Computed balance (always accurate, no desync)
create or replace view shop.point_balances
  with (security_invoker = true)
  as
  select customer_id, coalesce(sum(points), 0) as balance
  from shop.point_rewards
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

create or replace function shop.is_staff()
returns boolean
language sql
stable
security definer
set search_path = shop
as $$
  select coalesce(
    (select is_staff from shop.profiles where id = shop.get_current_user_id()),
    false
  );
$$;

grant execute on function shop.is_staff() to authenticated;

create or replace function shop.is_store_staff(p_store_id text)
returns boolean
language sql
stable
security definer
set search_path = shop
as $$
  select exists (
    select 1 from shop.store_staff
    where store_id = p_store_id
      and staff_id = shop.get_current_user_id()
      and deleted_at is null
  );
$$;

grant execute on function shop.is_store_staff(text) to authenticated;

-- Helper: does the current user own this order?
create or replace function shop.is_order_owner(p_order_id text)
returns boolean
language sql
stable
security definer
set search_path = shop
as $$
  select exists (
    select 1 from shop.orders
    where id = p_order_id
      and customer_id = shop.get_current_user_id()
  );
$$;

grant execute on function shop.is_order_owner(text) to authenticated;

-- Helper: is the product publicly visible?
create or replace function shop.is_product_visible(p_product_id text)
returns boolean
language sql
stable
security definer
set search_path = shop
as $$
  select exists (
    select 1 from shop.products
    where id = p_product_id
      and status = 'publish'
      and deleted_at is null
  );
$$;

grant execute on function shop.is_product_visible(text) to authenticated, anon;

-- ************************************************************
-- RLS PATTERN: JWT Claims-Based（app_metadata 超級管理員）
-- ************************************************************
-- 教學重點：
--   - auth.jwt() 回傳完整 JWT payload（包含 app_metadata）
--   - app_metadata 由後端設定，前端無法竄改（比 user_metadata 安全）
--   - 用途：跨店管理員、平台營運、客服角色
--
-- 設定方式：
--   UPDATE auth.users SET raw_app_meta_data =
--     raw_app_meta_data || '{"role":"super_admin"}'::jsonb
--   WHERE id = 'user-uuid';

create or replace function shop.is_super_admin()
returns boolean
language sql
stable
security definer
set search_path = shop
as $$
  select coalesce(
    (select auth.jwt()) -> 'app_metadata' ->> 'role' = 'super_admin',
    false
  );
$$;

grant execute on function shop.is_super_admin() to authenticated;

-- ************************************************************
-- RLS PATTERN: Time-Window（時效限制）
-- ************************************************************
-- 教學重點：
--   - 顧客只能在下單後 24 小時內取消訂單
--   - UPDATE policy 加上時間條件
--   - 超過時效 → policy 拒絕 → UPDATE 靜默返回 0 rows affected
--   - 搭配前端提示：「已超過取消期限，請聯繫客服」

create or replace function shop.can_cancel_order(p_order_id text)
returns boolean
language sql
stable
security definer
set search_path = shop
as $$
  select exists (
    select 1 from shop.orders
    where id = p_order_id
      and customer_id = shop.get_current_user_id()
      and status = 'pending'
      and created_at > now() - interval '24 hours'
  );
$$;

grant execute on function shop.can_cancel_order(text) to authenticated;

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
    execute format('alter table shop.%I enable row level security;', tbl);
  end loop;
end;
$$;

-- --- Policies ---

-- Users: read all, no direct writes (managed by trigger)
create policy "users_select"       on shop.users for select to authenticated using (true);
create policy "users_service_role" on shop.users for all to service_role using (true) with check (true);

-- Profiles: read all, update own
create policy "profiles_select"       on shop.profiles for select to authenticated using (true);
create policy "profiles_update_own"   on shop.profiles for update to authenticated using (id = shop.get_current_user_id());
create policy "profiles_service_role" on shop.profiles for all to service_role using (true) with check (true);

-- Products: published = public, draft = author/staff
create policy "products_select" on shop.products for select to authenticated, anon
  using (
    (status = 'publish' and deleted_at is null)
    or author_id = shop.get_current_user_id()
    or shop.is_staff()
  );
create policy "products_insert_staff" on shop.products for insert to authenticated
  with check (shop.is_staff());
create policy "products_update_staff" on shop.products for update to authenticated
  using (shop.is_staff());
create policy "products_delete_staff" on shop.products for delete to authenticated
  using (shop.is_staff());
create policy "products_service_role" on shop.products for all to service_role
  using (true) with check (true);

-- Product images: follow product visibility
create policy "product_images_select" on shop.product_images for select to authenticated, anon
  using (shop.is_product_visible(product_id) or shop.is_staff());
create policy "product_images_insert_staff" on shop.product_images for insert to authenticated
  with check (shop.is_staff());
create policy "product_images_update_staff" on shop.product_images for update to authenticated
  using (shop.is_staff());
create policy "product_images_delete_staff" on shop.product_images for delete to authenticated
  using (shop.is_staff());
create policy "product_images_service_role" on shop.product_images for all to service_role
  using (true) with check (true);

-- Reviews: visible = public, write own
create policy "reviews_select" on shop.reviews for select to authenticated, anon
  using (is_visible = true or customer_id = shop.get_current_user_id() or shop.is_staff());
create policy "reviews_insert_own" on shop.reviews for insert to authenticated
  with check (customer_id = shop.get_current_user_id());
create policy "reviews_update_own" on shop.reviews for update to authenticated
  using (customer_id = shop.get_current_user_id());
create policy "reviews_delete_staff" on shop.reviews for delete to authenticated
  using (shop.is_staff());
create policy "reviews_service_role" on shop.reviews for all to service_role
  using (true) with check (true);

-- Orders: customer sees own, staff sees all, super_admin sees all
create policy "orders_select" on shop.orders for select to authenticated
  using (
    customer_id = shop.get_current_user_id()
    or shop.is_staff()
    or shop.is_super_admin()   -- JWT claims pattern
  );
create policy "orders_insert" on shop.orders for insert to authenticated
  with check (customer_id = shop.get_current_user_id());
-- Staff / super_admin 可修改任何訂單
create policy "orders_update_staff" on shop.orders for update to authenticated
  using (shop.is_staff() or shop.is_super_admin());
-- 顧客可在 24 小時內取消自己的 pending 訂單（Time-Window pattern）
create policy "orders_cancel_own" on shop.orders for update to authenticated
  using (shop.can_cancel_order(id))
  with check (status = 'cancelled');  -- 只允許改成 cancelled
create policy "orders_service_role" on shop.orders for all to service_role
  using (true) with check (true);

-- Order items: inherit from parent order (via helper, no inline JOIN)
create policy "order_items_select" on shop.order_items for select to authenticated
  using (shop.is_order_owner(order_id) or shop.is_staff());
create policy "order_items_insert_staff" on shop.order_items for insert to authenticated
  with check (shop.is_order_owner(order_id) or shop.is_staff());
create policy "order_items_update_staff" on shop.order_items for update to authenticated
  using (shop.is_staff());
create policy "order_items_delete_staff" on shop.order_items for delete to authenticated
  using (shop.is_staff());
create policy "order_items_service_role" on shop.order_items for all to service_role
  using (true) with check (true);

-- Order coupons: inherit from parent order
create policy "order_coupons_select" on shop.order_coupons for select to authenticated
  using (shop.is_order_owner(order_id) or shop.is_staff());
create policy "order_coupons_insert_staff" on shop.order_coupons for insert to authenticated
  with check (shop.is_staff());
create policy "order_coupons_update_staff" on shop.order_coupons for update to authenticated
  using (shop.is_staff());
create policy "order_coupons_delete_staff" on shop.order_coupons for delete to authenticated
  using (shop.is_staff());
create policy "order_coupons_service_role" on shop.order_coupons for all to service_role
  using (true) with check (true);

-- Addresses: customer manages own
create policy "addresses_select" on shop.addresses for select to authenticated
  using (customer_id = shop.get_current_user_id() or shop.is_staff());
create policy "addresses_insert_own" on shop.addresses for insert to authenticated
  with check (customer_id = shop.get_current_user_id());
create policy "addresses_update_own" on shop.addresses for update to authenticated
  using (customer_id = shop.get_current_user_id());
create policy "addresses_delete_own" on shop.addresses for delete to authenticated
  using (customer_id = shop.get_current_user_id());
create policy "addresses_service_role" on shop.addresses for all to service_role
  using (true) with check (true);

-- Payments: customer views own, staff manages
create policy "payments_select" on shop.payments for select to authenticated
  using (customer_id = shop.get_current_user_id() or shop.is_staff());
create policy "payments_insert" on shop.payments for insert to authenticated
  with check (customer_id = shop.get_current_user_id() or shop.is_staff());
create policy "payments_update_staff" on shop.payments for update to authenticated
  using (shop.is_staff());
create policy "payments_service_role" on shop.payments for all to service_role
  using (true) with check (true);

-- Point rewards: customer views own
create policy "point_rewards_select" on shop.point_rewards for select to authenticated
  using (customer_id = shop.get_current_user_id() or shop.is_staff());
create policy "point_rewards_insert_staff" on shop.point_rewards for insert to authenticated
  with check (shop.is_staff());
create policy "point_rewards_service_role" on shop.point_rewards for all to service_role
  using (true) with check (true);

-- Stores: public read
create policy "stores_select" on shop.stores for select to authenticated, anon using (true);

-- Companies: staff only
create policy "companies_select" on shop.companies for select to authenticated
  using (shop.is_staff());

-- Stocks / inventory: staff + store-level staff
create policy "stocks_select" on shop.stocks for select to authenticated
  using (shop.is_staff() or shop.is_store_staff(store_id));
create policy "inventory_movements_select" on shop.inventory_movements for select to authenticated
  using (shop.is_staff() or shop.is_store_staff(store_id));

-- Coupons: active & valid = public, all = staff
create policy "coupons_select" on shop.coupons for select to authenticated, anon
  using (
    (is_active = true and deleted_at is null
     and (starts_at is null or starts_at <= now())
     and (expires_at is null or expires_at > now()))
    or shop.is_staff()
  );

-- Store staff: own record or global staff
create policy "store_staff_select" on shop.store_staff for select to authenticated
  using (staff_id = shop.get_current_user_id() or shop.is_staff());

-- Terms / taxonomy: public read
create policy "terms_select" on shop.terms for select to authenticated, anon using (true);
create policy "term_taxonomy_select" on shop.term_taxonomy for select to authenticated, anon using (true);
create policy "term_relationships_select" on shop.term_relationships for select to authenticated, anon using (true);

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
      create policy "%1$s_insert_staff" on shop.%1$s for insert to authenticated
        with check (shop.is_staff());
      create policy "%1$s_update_staff" on shop.%1$s for update to authenticated
        using (shop.is_staff());
      create policy "%1$s_delete_staff" on shop.%1$s for delete to authenticated
        using (shop.is_staff());
      create policy "%1$s_service_role" on shop.%1$s for all to service_role
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
    execute format('grant select on shop.%I to authenticated;', tbl);
    execute format('grant insert, update, delete on shop.%I to authenticated;', tbl);
    execute format('grant all on shop.%I to service_role;', tbl);
  end loop;

  -- Public-readable tables: anon can SELECT
  foreach tbl in array array[
    'products', 'product_images', 'stores',
    'terms', 'term_taxonomy', 'term_relationships',
    'coupons', 'reviews'
  ]
  loop
    execute format('grant select on shop.%I to anon;', tbl);
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
      drop trigger if exists trg_%1$s_updated_at on shop.%1$s;
      create trigger trg_%1$s_updated_at
        before update on shop.%1$s
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
      drop trigger if exists trg_%1$s_audit on shop.%1$s;
      create trigger trg_%1$s_audit
        before insert or update on shop.%1$s
        for each row execute function shop.handle_audit_fields();
    ', tbl);
  end loop;
end;
$$;

-- Supabase Realtime (enable via Dashboard or SQL)
-- Only on tables that benefit from live updates:
--
-- alter publication supabase_realtime add table shop.orders;
-- alter publication supabase_realtime add table shop.stocks;
-- alter publication supabase_realtime add table shop.payments;
-- alter publication supabase_realtime add table shop.reviews;

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
--   with check (bucket_id = 'product-images' and shop.is_staff());
--
-- create policy "product_images_staff_delete"
--   on storage.objects for delete to authenticated
--   using (bucket_id = 'product-images' and shop.is_staff());
