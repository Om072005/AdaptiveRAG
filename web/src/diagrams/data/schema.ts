// The README "Graph schema" as the tables it became. One deviation from the README: an alias is
// keyed by surface form and entity together, so one name can point at two different people.
import type { DiagramData } from '../types.ts'
import { box, edge } from './shapes.ts'

export const SCHEMA: DiagramData = {
  id: 'schema',
  title: 'Graph schema',
  desc: 'Entities have aliases and take part in relations as subject or object. Every relation is extracted from one chunk, which is part of one document; the database refuses a relation without its chunk.',
  nodes: [
    { id: 'entities', lines: ['entities', 'canonical_id, key', 'canonical_name, type', 'embedding'], kind: 'store', detail: 'One row per resolved entity; the type comes from a closed list.', module: 'db/migrations/0001_init.sql' },
    { id: 'aliases', lines: ['aliases', 'key: surface_form', 'and canonical_id', 'confidence'], kind: 'store', detail: 'The surface forms that name an entity. Keyed by name and entity together, so two people sharing a name keep one row each.', module: 'db/migrations/0001_init.sql' },
    { id: 'relations', lines: ['relations', 'rel_id, key', 'subject_id, predicate, object_id', 'chunk_id, never empty', 'evidence offsets, confidence', 'embedding'], kind: 'store', detail: 'One fact between two entities, with the character span of its evidence and the chunk it came from.', module: 'db/migrations/0001_init.sql' },
    { id: 'chunks', lines: ['chunks', 'chunk_id, key', 'doc_id, strategy, offsets', 'text, embedding'], kind: 'store', detail: 'A span of a document, for one chunking strategy, with its embedding.', module: 'db/migrations/0001_init.sql' },
    { id: 'documents', lines: ['documents', 'doc_id, key', 'source, title, text'], kind: 'store', detail: 'A normalized HotpotQA paragraph with the offsets of its sentences.', module: 'db/migrations/0001_init.sql' },
  ],
  edges: [
    edge('entities', 'relations', 'subject of', undefined, 'subject'),
    edge('entities', 'relations', 'object of', undefined, 'object'),
    edge('entities', 'aliases', 'known as'),
    edge('relations', 'chunks', 'extracted from', 'dotted'),
    edge('chunks', 'documents', 'part of'),
  ],
  wide: {
    width: 1024,
    height: 384,
    nodes: {
      entities: box(136, 112, 240, 112),
      aliases: box(136, 296, 240, 112),
      relations: box(488, 112, 272, 144),
      chunks: box(856, 112, 240, 112),
      documents: box(856, 296, 240, 96),
    },
    bends: {
      subject: [[304, 80]],
      object: [[304, 136]],
    },
    labels: {
      subject: [304, 80],
      object: [304, 136],
      'relations-chunks': [680, 112],
    },
  },
  tall: {
    width: 352,
    height: 904,
    nodes: {
      aliases: box(176, 64, 240, 112),
      entities: box(176, 240, 240, 112),
      relations: box(176, 440, 288, 144),
      chunks: box(176, 648, 256, 112),
      documents: box(176, 832, 256, 96),
    },
    bends: {
      subject: [[120, 336]],
      object: [[232, 336]],
    },
    labels: {
      subject: [120, 328],
      object: [232, 336],
      'entities-aliases': [176, 152],
    },
  },
}
