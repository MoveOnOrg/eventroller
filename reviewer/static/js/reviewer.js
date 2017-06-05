"use strict";
/*
  Reviewer needs to:
  * init with:
    - current organization
    - content type
    - api_path (default='/review')
    - css selector to search (default='.review')
    - dict of review fields/options (default=<see current>)
  * get ids from current dom
    * create fields in a good location
    * handle log/review saving
    * handle marking attention
  * poll for new info
    * match dom ids with info and update
      * ?do NOT update if user is attending (or update differently)
 */
function Reviewer() {
  this.init(arguments);
  this.state = {}; //keyed by object_id; has pointers to dom, and current values
  this.attention = null; //key of object
  this.prefix = 'reviewer_'+parseInt(Math.random()*100) + '_';
  this.opt = {
    jQuery: window.jQuery,
    organization: null,
    content_type: null,
    api_path: '/review',
    css_selector: '.review', //expects data-pk and data-type
    schema: {
      'review_status': [
        ['unknown', 'unreviewed'],
        ['good', 'good'],
        ['bad', 'bad'],
      ]
    }
  };
}
Reviewer.prototype = {
  init: function(){},


  //render review component for a specific field
  render: function($) {
    return (''
      + '<div class="review-widget">'
      + ''
      + ''
      + ''
      + ''
      + ''
      + ''
      + ''
      + ''
      + ''
      + '</div>'
    )
  },
  renderLog: function(){},
  renderDecisions: function(name, schema, obj) {
    var prefix = this.prefix;
    '<select class="review-'+name+'" onchange="" data-pk="'+obj.pk+'" name="'+prefix+name++obj.pk+'">'
    + schema.map(function(o) {
      return '<option '+(obj[name]==o[0]?'selected':'')+' value="'+o[0]+'">'+o[1]+'</option>';
    }).join('')
    + '</select>';
  },
  renderAttention: function(){}
}
