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

/** initial is the route the reason led to; relational questions go hybrid since decision D17. */
export function reasonText(reason: string, initial?: string): string {
  const [head, rest = ''] = reason.split(':', 2)
  switch (head) {
    case 'forced':
      return `This run asked for ${ROUTE[rest] ?? rest}, so the router did not choose.`
    case 'ambiguous': {
      const [label, conf] = rest.split(' ')
      return `The classifier was unsure (${(LABEL[label] ?? label).toLowerCase()} at ${conf}), so the router used hybrid.`
    }
    case 'relational': {
      const kind = rest === 'comparison' ? 'a comparison' : 'multi hop'
      if (initial === 'hybrid') {
        return `The question is ${kind}, so the router used hybrid: graph paths and vector hits ranked together, which beat graph traversal alone on the dev questions.`
      }
      return `The question is ${kind} and its entities are in the graph, so the router walked the graph.`
    }
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

/** The model selector's reason string (generate/select.py) as a sentence. */
export function selectText(reason: string): string {
  const m = reason.match(/^(small|large):(.*)$/)
  if (!m) return reason
  const detail = m[2].trim()
  const route = detail.match(/^route (\w+)$/)
  if (route) return `The ${ROUTE[route[1]] ?? route[1]} route brings harder context, so the large model answered.`
  const label = detail.match(/^label (\w+)$/)
  if (label) {
    return `The question is ${label[1] === 'comparison' ? 'a comparison' : 'multi hop'}, so the large model answered.`
  }
  const context = detail.match(/^context (\d+) tokens > (\d+)$/)
  if (context) {
    return `The context was ${context[1]} tokens, above the ${context[2]} token limit for the small model, so the large model answered.`
  }
  const small = detail.match(/^route (\w+), label (\w+), (\d+) tokens$/)
  if (small) {
    const kind = small[2] === 'none' ? 'an unclassified question' : `a ${(LABEL[small[2]] ?? small[2]).toLowerCase()} question`
    return `A ${ROUTE[small[1]] ?? small[1]} route, ${kind} and ${small[3]} tokens of context fit the small model.`
  }
  return reason
}
