-- MandiRates marketplace schema for Supabase (Postgres).
-- NOT yet run on a real database. Paste it in Supabase > SQL Editor > Run, and send me any error.

create table profiles(
  id uuid primary key references auth.users on delete cascade,
  email text,
  phone text check (phone is null or phone ~ '^[6-9][0-9]{9}$'),
  name text,
  verified boolean not null default false,
  premium_until timestamptz,
  created_at timestamptz not null default now());

create table listings(
  id bigint generated always as identity primary key,
  owner uuid not null references profiles(id) on delete cascade,
  kind text not null check (kind in ('sell','buy')),
  crop text not null check (length(crop) between 2 and 40),
  qty_quintal numeric not null check (qty_quintal >= 1),
  price_per_quintal numeric not null check (price_per_quintal between 1 and 500000),
  state text not null check (length(state) between 2 and 40),
  district text check (length(district) <= 40),
  note text check (length(note) <= 300),
  owner_verified boolean not null default false,
  status text not null default 'active' check (status in ('active','hidden','sold')),
  created_at timestamptz not null default now());
create index listings_active_idx on listings (status, created_at desc);

create table reports(
  id bigint generated always as identity primary key,
  listing_id bigint not null references listings(id) on delete cascade,
  reporter uuid not null references profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (listing_id, reporter));

create table contact_views(
  user_id uuid not null references profiles(id) on delete cascade,
  listing_id bigint not null references listings(id) on delete cascade,
  day date not null default current_date,
  primary key (user_id, listing_id, day));

alter table profiles enable row level security;
alter table listings enable row level security;
alter table reports enable row level security;
alter table contact_views enable row level security;

-- Column-level rights: people can never set 'verified' or 'premium_until' themselves.
revoke all on profiles, listings, reports, contact_views from anon, authenticated;
grant select on profiles to authenticated;
grant insert (id, email, phone, name) on profiles to authenticated;
grant update (id, email, phone, name) on profiles to authenticated;
grant select on listings to anon, authenticated;
grant insert (owner, kind, crop, qty_quintal, price_per_quintal, state, district, note) on listings to authenticated;
grant update (status) on listings to authenticated;
grant insert (listing_id, reporter) on reports to authenticated;

-- Phone numbers live in profiles. Nobody can read another person's profile.
create policy "own profile read" on profiles for select to authenticated using (auth.uid() = id);
create policy "own profile insert" on profiles for insert to authenticated with check (auth.uid() = id);
create policy "own profile update" on profiles for update to authenticated using (auth.uid() = id) with check (auth.uid() = id);
create policy "anyone reads active listings" on listings for select to anon, authenticated using (status = 'active' or owner = auth.uid());
create policy "owner inserts" on listings for insert to authenticated with check (auth.uid() = owner);
create policy "owner updates own, not reported ones" on listings for update to authenticated using (auth.uid() = owner and status <> 'hidden') with check (auth.uid() = owner and status in ('active','sold'));
create policy "report as yourself" on reports for insert to authenticated with check (auth.uid() = reporter);

-- Copy the seller's verified flag onto a new listing (people cannot set it themselves).
create function set_owner_verified() returns trigger language plpgsql security definer set search_path = public as $$
begin new.owner_verified := coalesce((select verified from profiles where id = new.owner), false); return new; end $$;
create trigger listings_verified before insert on listings for each row execute function set_owner_verified();

-- Three reports hide a listing for review.
create function hide_reported() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from reports where listing_id = new.listing_id) >= 3 then
    update listings set status = 'hidden' where id = new.listing_id and status = 'active';
  end if;
  return new;
end $$;
create trigger reports_hide after insert on reports for each row execute function hide_reported();

-- Contact numbers are released only through this function.
-- Premium: unlimited. Free: 3 different listings per day. Returns 'LIMIT' when the free limit is used up.
create function get_contact(lid bigint) returns text language plpgsql security definer set search_path = public as $$
declare ph text; prem boolean; n int;
begin
  if auth.uid() is null then return null; end if;
  select p.phone into ph from listings l join profiles p on p.id = l.owner where l.id = lid and l.status = 'active';
  if ph is null then return null; end if;
  select coalesce(premium_until > now(), false) into prem from profiles where id = auth.uid();
  if prem then return ph; end if;
  if exists (select 1 from contact_views where user_id = auth.uid() and listing_id = lid and day = current_date) then return ph; end if;
  select count(*) into n from contact_views where user_id = auth.uid() and day = current_date;
  if n >= 3 then return 'LIMIT'; end if;
  insert into contact_views (user_id, listing_id) values (auth.uid(), lid);
  return ph;
end $$;
revoke all on function get_contact(bigint) from public, anon;
grant execute on function get_contact(bigint) to authenticated;
