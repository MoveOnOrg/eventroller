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
    * handle marking focus
  * poll for new info
    * match dom ids with info and update
      * ?do NOT update if user is attending (or update differently)
 */
function Reviewer(opts) {
  this.state = {}; //keyed by object_id; has pointers to dom, and current values
  this.focus = null; //key of object
  this.prefix = 'reviewer_'+parseInt(Math.random()*100) + '_';
  this.opt = {
    jQuery: window.jQuery,
    organization: null,
    contentType: null,
    apiPath: '/review',
    cssSelector: '.review', //expects data-pk and data-type
    schema: [
      {'name': 'review_status',
       'choices':[ ['unknown', 'unreviewed'],
                   ['good', 'good'],
                   ['bad', 'bad']],
       'label': 'Review Status'
      }
    ]
  };
  this.init(opts);
}
Reviewer.prototype = {
  init: function(options){
    if (options) {
      for (var a in options) {
        this.opt[a] = options[a];
      }
    }
    for (var b in this) {
      if (typeof this[b] == 'function') {
        this[b] = this[b].bind(this);
      }
    }
    var $ = this.$ = this.opt.jQuery;
  },
  run: function() {
    this.initReviewWidgets();
    this.updateMissingData(this.initRenderAll);
    // 2. render the data/initialize the widget
    //2. start polling
    return this;
  },
  saveDecision: function(evt) {
  },
  findReviewWidgets: function() {
    var $ = this.opt.jQuery;
    return $(this.opt.cssSelector);
  },
  initReviewWidgets: function() {
    var self = this;
    this.findReviewWidgets().each(function() {
      self.loadDataFromReviewWidget(this)
    });
  },
  loadDataFromReviewWidget: function(widget) {
    //get pk, dom and => this.state
    var $ = this.opt.jQuery;
    var pk = $(widget).attr('data-pk');
    if (!(this.state[pk])) {
      this.state[pk] = {'pk': pk, 'o': widget, 'data': null};
    }
  },
  updateMissingData: function(callback) {
    var newPks = [];
    for (var a in this.state) {
      if (!this.state[a].data) {
        newPks.push(a);
      }
    }
    this.loadMissingData(newPks, callback);
  },
  loadMissingData: function(pks, callback) {
    var self = this;
    this.$.getJSON(this.opt.apiPath + '/history/' + this.opt.organization
                   + '/?logs=1&type=' + this.opt.contentType + '&pks=' + pks.join(','))
      .then(function(data) {
        if (data.reviews && data.reviews.length == pks.length) {
          // In theory, the api delivers the reviews and logs back in the same
          // order as they were asked for.
          // So data.logs[i] should be for pks[i], but when there
          // hasn't been a review yet, what does redis return?
          // Thus this is defensive and uses the review and log pk vals rather than
          // the pk index.
          for (var i=0,l=pks.length; i<l; i++) {
            var rev = data.reviews[i];
            var log = data.logs[i];
            if (rev) {
                if (self.state[rev.pk]) {
                  self.state[rev.pk].data = rev;
                }
            } else { //no data for that pk
              self.state[pks[i]].data = {};
            }
            if (log && self.state[log.pk]) {
              self.state[rev.pk].log = log.m;
            }
          }
        }
        if (callback) {
          callback(data);
        }
      });
  },
  pollState: function() {
    //1. find pks with missing data
    //2. get full data with state for them
    //3. get current/
    //   3.1: update state
    //   3.2: update UI
  },
  initRenderAll: function() {
    for (var a in this.state) {
      var obj = this.state[a];
      if (obj.o) {
        obj.o.innerHTML = this.render(obj);
        this.postRender(obj);
      }
    }
  },
  //render review component for a specific field
  render: function(obj) {
    var self = this;
    return (''
            + '<div class="review-widget">'
            + this.renderFocus()
            + this.opt.schema.map(function(schema) {
              return self.renderDecisions(schema, obj)
            }).join('')
            + '<label>Log</label><input type="text" />'
            + '<button class="save">Save</button>'
            + this.renderLog(obj)
            + '</div>'
           )
  },
  renderLog: function(){return '<div>Log</div>'},
  renderDecisions: function(schema, obj) {
    var prefix = this.prefix;
    var name = schema.name;
    return (''
            + '<div><label>'+schema.label+'</label>'
            + '<select class="review-select-'+name+'" data-pk="'+obj.pk+'" name="'+prefix+name+'_'+obj.pk+'">'
            + schema.choices.map(function(o) {
              return '<option '+(obj.data[name]==o[0]?'selected="selected"':'')+' value="'+o[0]+'">'+o[1]+'</option>';
            }).join('')
            + '</select></div>');
  },
  renderFocus: function(){return '<div>focus</div>'},
  postRender: function(obj) {
    var $ = this.$;
    var self = this;
    $('button.save', obj.o).on('click', function(evt) {
      evt.preventDefault(); //disable submitting page
      //TODO: save log+review
    });
    $('input,select', obj.o).on('click mousedown focus', function(evt) {
      //TODO: mark attention if different pk
    });
  }
};
