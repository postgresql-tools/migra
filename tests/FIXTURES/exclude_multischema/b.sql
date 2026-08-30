create schema schema1;

create table schema1.t(id uuid, value text, name text);

create schema schema2;

create table schema2.x(id uuid, value text);

create table schema2.y(id uuid, value text);

create schema schema3;

create table schema3.untouched(id uuid);

create table schema3.should_be_ignored(id uuid);

create table public.other(id uuid);
