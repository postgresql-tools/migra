create schema schema1;

create table schema1.t(id uuid, value text);

create schema schema2;

create table schema2.x(id uuid, value text);

create schema schema3;

create table schema3.untouched(id uuid);

create table public.other(id uuid, value text);
