-- Triples under extract.min_confidence (config/ingest.toml) are rejected and logged like the others.
alter table extraction_rejects drop constraint extraction_rejects_reason_check;
alter table extraction_rejects add constraint extraction_rejects_reason_check
  check (reason in ('subject_not_in_source','object_not_in_source','bad_json','empty','self_loop','low_confidence'));
