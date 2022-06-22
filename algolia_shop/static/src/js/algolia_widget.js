odoo.define('algolia_shop.algolia_shop', function (require) {
  'user strict';
  var publicWidget = require('web.public.widget');
  var ajax = require('web.ajax');
  publicWidget.registry.AlgoliaShop = publicWidget.Widget.extend({
    selector: '.algo-shop-engine',
    start: function () {
      this._initialize_instantsearch();
      return this._super.apply(this, arguments);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
    * @private
    */
    _initialize_instantsearch: function () {
      var self = this;
      this._get_index_information().then(function (result) {
        self.index_information = result;
        // refinementList
        var refinement = {}
        // var attribute_name = $('#shop-details').data('attribute-name');
        // attribute_name.forEach(attribute => { refinement[attribute[0]] = [attribute[1]] })
        // // attribute filter
        // var attribute_line_name = $('#shop-details').data('attribute-line-name');
        var hierarchical_depth = $('#shop-details').data('depth-category');
        var index_name = result.index
        var hierarchical_list = [];
        if (hierarchical_depth) { for (let i = 0; i < hierarchical_depth; i++) { hierarchical_list.push('category_lvl' + i) } }
        // Variable initialUiState
        var objInitState = {}
        objInitState[index_name] = self._get_initial_state(refinement);
        const search = instantsearch({
          indexName: index_name,
          searchClient: algoliasearch(result.app_id, result.search_key),
          initialUiState: objInitState,
          routing: true
        })
        var odoo_widget = [
          instantsearch.widgets.searchBox(self._get_widget_searchbox()),
          instantsearch.widgets.hits(self._get_widget_hits()),
          // instantsearch.widgets.hierarchicalMenu(self._get_widget_hierachicalMenu(hierarchical_list)),
          instantsearch.widgets.pagination(self._get_widget_pagination()),
          instantsearch.widgets.stats(self._get_widget_stats()),
          instantsearch.widgets.hitsPerPage(self._get_hits_per_page())
        ]
        // attribute_line_name.forEach(element => {
        //   var type_attribute = $('#shop-details').data('type-attribute');
        //   if (type_attribute.color.includes(element[0])) {
        //     odoo_widget.push(instantsearch.widgets.refinementList(self._get_widget_refinementColor(element)))
        //   } else if (type_attribute.select.includes(element[0])) {
        //     odoo_widget.push(instantsearch.widgets.menuSelect(self._get_widget_menuSelect(element)))
        //   } else {
        //     odoo_widget.push(instantsearch.widgets.refinementList(self._get_widget_refinementOther(element)))
        //   }
        // });
        odoo_widget.push(instantsearch.widgets.sortBy(self._get_widget_sortBy(index_name)))
        search.addWidgets(odoo_widget);
        search.start();
      }).catch(function (result) { console.log(result) })
    },
    _get_initial_state: function (refinement) {
      return {
        refinementList: refinement,
        hierarchicalMenu: {
          category_lvl0: [$('#shop-details').data('category-route')]
        },
        query: $('#shop-details').data('search'),
        page: $('#shop-details').data('page')
      }
    },
    _get_widget_searchbox: function () {
      return {
        container: '#searchbox',
        placeholder: 'Search Product, Brand, category ...',
      }
    },
    _get_widget_hits: function () {
      return {
        container: '#hits',
        templates: {
          item: '<form action="/shop/engine/cart/update" method="post" class="form_item_container">' +
            '<div class="item_container"><div class="card-body p-1 oe_product_image">' +
            '<span class="d-flex h-100 justify-content-center align-items-center">' +
            '<img src={{ image }} class="img img-fluid"/></span>' +
            '</div><div class="card-body p-0 text-center o_wsale_product_information">' +
            '<a href=/shop/engine/product/{{ objectID }}>' +
            '<span>{{#helpers.highlight}}{ "attribute": "name" }{{/helpers.highlight}}</span>' +
            '</a>' +
            '<p>. Price <b>{{ price }}.00</b> Ariary</p></div>' +
            '<input name="object_id" value="{{ objectID }}" type="hidden"/>' +
            '<a role="button" class="btn btn-primary btn-block a-submit" href="#"><i class="fa fa-shopping-cart"></i> Add to Cart</a>' +
            '</div></form>',
        },
      }
    },
    _get_widget_hierachicalMenu: function (hierarchical_list) {
      return {
        container: '#hierarchical-menu',
        attributes: hierarchical_list,
      }
    },
    _get_widget_pagination: function () {
      return {
        container: '#pagination',
        showFirst: false,
        showLast: false,
        templates: {
            previous: 'Prev.',
            next:'Next'
        },

      }
    },
    _get_widget_stats: function () {
      return {
        container: '#stats',
      }
    },
    _get_widget_sortBy: function (index_name) {
      return {
        container: '#sort-by',
        items: [
          { label: 'Featured', value: index_name },
          { label: 'Price (asc)', value: index_name + '_price_asc' },
          { label: 'Price (desc)', value: index_name + '_price_desc' },
        ],
      }
    },
    _get_widget_refinementColor: function (element) {
      return {
        container: '#' + element[1].replace(' ', '_').replace('+','_').replace('(','_').replace(')','_'),
        attribute: element[0],
        templates: {
          item: '<label style="text-align:center;background-color:{{ value }};width: 25px;height: 25px;border: groove;">{{ count }}</label>'
        }
      }
    },
    _get_widget_menuSelect: function (element) {
      return {
        container: '#' + element[1].replace(' ', '_').replace('+','_').replace('(','_').replace(')','_'),
        attribute: element[0],
      }
    },
    _get_widget_refinementOther: function (element) {
      return {
        container: '#' + element[1].replace(' ', '_').replace('+','_').replace('(','_').replace(')','_'),
        templates: {
          searchableNoResults: 'No results',
        },
        attribute: element[0],
        limit: 5,
        showMore: true,
      }
    },
    _get_index_information: function () {
      return new Promise(function (resolve, reject) {
        ajax.jsonRpc('/website/index', 'call').then(function (response) {
          resolve(response);
        }).catch(function (error) {
          reject(error);
        });
      });

    },
    _get_hits_per_page: function (){
        return {
          container: '#hit-per-page',
          items: [
            { label: '20', value: 20, default: true },
            { label: '40', value: 40 },
            { label: '60', value: 60 },
            { label: '80', value: 80 }
          ]
        }
    }
  })
  return publicWidget.registry.AlgoliaShop;
})
