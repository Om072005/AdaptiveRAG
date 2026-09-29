// Router reason and fallback strings (contract decision table) as sentences a reader understands.
// An unknown string is shown as it is, never hidden.

export const LABEL: Record<string, string> = {
  single_hop: 'Single hop',
  multi_hop: 'Multi hop',
  comparison: 'Comparison',
}

export const METHOD: Record<string, string> = {
  rules: 'hand written rules',
  logreg: 'logistic regression',
  llm: 'a language model',
}

const ROUTE: Record<string, string> = { vector: 'vector search', graph: 'graph traversal', hybrid: 'hybrid' }

export function reasonText(reason: string): string {
  const [head, rest = ''] = reason.split(':', 2)
  switch (head) {
    case 'forced':
      return `This run asked for ${ROUTE[rest] ?? rest}, so the router did not choose.`
    case 'ambiguous': {
      const [label, conf] = rest.split(' ')
      return `The classifier was unsure (${(LABEL[label] ?? label).toLowerCase()} at ${conf}), so the router used hybrid.`
    }
    case 'relational':
      return `The question is ${rest === 'comparison' ? 'a comparison' : 'multi hop'} and its entities are in the graph, so the router walked the graph.`
    case 'no_relational_structure':
      return 'The question asks for one fact, with no relation or comparison, so vector search is enough.'
    case 'entities_not_in_graph':
      return 'The question is relational, but none of its entities was found in the graph, so the router used vector search.'
    case 'low_budget':
      return 'The query budget was low, so the router kept to the cheaper vector route.'
  }
  return fallbackText(reason)
}

export function fallbackText(fallback: string): string {
  const name = fallback.split('->')[0]
  if (name === 'vector_low_score') return 'Vector search scored below the threshold, so the router tried hybrid.'
  if (name === 'graph_no_path') return 'Graph traversal found no connected path, so the router tried hybrid.'
  return fallback
}
