export function appendSearch(destination, sourceSearch) {
  if (!sourceSearch) return destination
  const query = sourceSearch.startsWith('?') ? sourceSearch.slice(1) : sourceSearch
  if (!query) return destination
  return `${destination}${destination.includes('?') ? '&' : '?'}${query}`
}
