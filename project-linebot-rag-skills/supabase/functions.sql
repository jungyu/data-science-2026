create or replace function match_private_knowledge(
  query_embedding vector(1536),
  query_text text,
  match_count int default 8,
  category_filter text[] default null
)
returns table (
  id uuid,
  title text,
  content text,
  category text,
  metadata jsonb,
  vector_score float,
  keyword_score float,
  combined_score float
)
language sql stable
as $$
  with vector_matches as (
    select
      pk.id,
      1 - (pk.embedding <=> query_embedding) as vector_score,
      row_number() over (order by pk.embedding <=> query_embedding) as vector_rank
    from private_knowledge pk
    where pk.embedding is not null
      and (category_filter is null or pk.category = any(category_filter))
    order by pk.embedding <=> query_embedding
    limit match_count * 3
  ),
  keyword_matches as (
    select
      pk.id,
      ts_rank(pk.search_vector, plainto_tsquery('simple', query_text)) as keyword_score,
      row_number() over (
        order by ts_rank(pk.search_vector, plainto_tsquery('simple', query_text)) desc
      ) as keyword_rank
    from private_knowledge pk
    where pk.search_vector @@ plainto_tsquery('simple', query_text)
      and (category_filter is null or pk.category = any(category_filter))
    limit match_count * 3
  ),
  fused as (
    select
      pk.id,
      pk.title,
      pk.content,
      pk.category,
      pk.metadata,
      coalesce(vm.vector_score, 0) as vector_score,
      coalesce(km.keyword_score, 0) as keyword_score,
      (
        coalesce(1.0 / (60 + vm.vector_rank), 0) +
        coalesce(1.0 / (60 + km.keyword_rank), 0)
      ) as combined_score
    from private_knowledge pk
    left join vector_matches vm on pk.id = vm.id
    left join keyword_matches km on pk.id = km.id
    where vm.id is not null or km.id is not null
  )
  select *
  from fused
  order by combined_score desc
  limit match_count;
$$;
