angular = require('angular')
mail = require('./vendor/jwz')


module.exports = class StreamController
  this.$inject = [
    '$scope', '$route', '$rootScope', '$routeParams',
    'queryParser', 'searchFilter', 'store',
    'streamer', 'streamFilter', 'threading', 'annotationMapper'
  ]
  constructor: (
     $scope,   $route,   $rootScope,   $routeParams
     queryParser,   searchFilter,   store,
     streamer,   streamFilter,   threading,   annotationMapper
  ) ->
    offset = 0

    fetch = (limit) ->
      options = {offset, limit}
      searchParams = searchFilter.toObject($routeParams.q)
      query = angular.extend(options, searchParams)
      query._separate_replies = true
      store.SearchResource.get(query, load)

    load = ({rows, replies}) ->
        offset += rows.length
        annotationMapper.loadAnnotations(rows, replies)

    # Disable the thread filter (client-side search)
    $scope.$on '$routeChangeSuccess', ->
      if $scope.threadFilter?
        $scope.threadFilter.active(false)
        $scope.threadFilter.freeze(true)

    # Reload on query change (ignore hash change)
    lastQuery = $routeParams.q
    $scope.$on '$routeUpdate', ->
      if $routeParams.q isnt lastQuery
        $route.reload()

    # Initialize the base filter
    streamFilter
      .resetFilter()
      .setMatchPolicyIncludeAll()

    # Apply query clauses
    terms = searchFilter.generateFacetedFilter $routeParams.q
    queryParser.populateFilter streamFilter, terms
    streamer.setConfig('filter', {filter: streamFilter.getFilter()})

    # Perform the initial search
    fetch(20)

    $scope.isStream = true
    $scope.sortOptions = ['Newest', 'Oldest']
    $scope.sort.name = 'Newest'
    $scope.threadRoot = threading.root
    $scope.loadMore = fetch
