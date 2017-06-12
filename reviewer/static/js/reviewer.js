"use strict";
/*
  Reviewer needs to:
  * init with:
    - current organization
    - content type
    - api path (default='/review')
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
  this.focus = null; //key of object for current user's focus
  this.lastUpdate = 0;
  this.prefix = 'reviewer_'+parseInt(Math.random()*100) + '_';
  this.opt = {
    jQuery: window.jQuery,
    organization: null,
    contentType: null,
    apiPath: '/review',
    cssSelector: '.review', //expects data-pk and data-type
    pollRate: 15, //number of seconds between polling for updates (0 means never)
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
  start: function() {
    this.initReviewWidgets();
    this.updateMissingData(this.initRenderAll);
    var poll = this.opt.pollRate;
    if (poll) {
      setInterval(this.pollState, poll * 1000);
    }
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
    this.loadReviewData(newPks, callback);
  },
  loadReviewData: function(pks, callback) {
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
  postFocus: function(pk, callback) {
    var opt = this.opt;
    this.$.ajax({
      'url': (opt.apiPath + '/focus/' + [opt.organization, opt.contentType, pk, ''].join('/')),
      'method': 'POST'
    }).then(function() {
      if (callback) {
        callback();
      }
    });
  },
  saveReview: function(reviewSubject, log, callback) {
    var opt = this.opt;
    var decisions = [];
    for (var i=0,l=opt.schema.length;i<l;i++) {
      var name = opt.schema[i].name;
      if (name in reviewSubject.data) {
        decisions.push(name + ':' + reviewSubject.data[name]);
      }
    }
    var csrfmiddlewaretoken = undefined;
    if (document.forms[0] && document.forms[0]['csrfmiddlewaretoken']) {
      csrfmiddlewaretoken = document.forms[0]['csrfmiddlewaretoken'].value;
    }
    this.$.ajax({
      'url': (opt.apiPath + ['', opt.organization, opt.contentType, reviewSubject.pk, ''].join('/')),
      'method': 'POST',
      'data': {
        csrfmiddlewaretoken: csrfmiddlewaretoken,
        content_type: opt.contentType,
        pk: reviewSubject.pk,
        decisions: decisions.join(';'),
        log: log
      }
    }).then(function() {
      if (log) {
        if (!reviewSubject.log) { reviewSubject.log = []; }
        reviewSubject.log.unshift({"m":log,
                         "r":'<i>me</i>',
                         "ts":parseInt(Number(new Date())/1000)})
      }
      if (callback) { callback(); }
    });
  },
  pollState: function() {
    var self = this;
    var opt = this.opt;
    this.$.getJSON(opt.apiPath + '/current/' + opt.organization + '/')
      .then(function(data) {
        var last = self.lastUpdate;
        var newLast = 0;
        // 1. update current focus state
        var newFocus = {};
        for (var i=0,l=data.focus.length; i<l; i++) {
          // f = [<event type id>, <pk>, "<name>", <timestamp in epoch seconds>]
          var f = data.focus[i];
          // We don't test lastUpdate for focus because we cleared focus from before
          if (opt.contentType == f[0] && f[1] in self.state) {
            newFocus[f[1]] = f[2];
          }
        }
        // 2. update focus dom
        (window.requestAnimationFrame||window.setTimeout)(function() {
          var oldFocus = self.focus;
          self.focus = newFocus;
          // not just update new focii, but clear old
          for (var pk in self.state) {
            if (pk in newFocus) {
              if (newFocus[pk] != self.state[pk].focus) {
                self.state[pk].focus = newFocus[pk];
                self.renderFocusUpdate(self.state[pk]);
              }
            } else {
              delete self.state[pk].focus;
              self.renderFocusUpdate(self.state[pk]);
            }
          }
        },0);
        // 3. update objects and update dom async-ly
        var changedPks = [];
        for (var i=0,l=data.reviews.length; i<l; i++) {
          var review = data.reviews[i];
          if (review.pk in self.state
              && opt.contentType == review.type
              && (!review.ts || review.ts > last)) {
            last = Math.max(last, review.ts || 0);
            changedPks.push(review.pk);
            var reviewSubject = self.state[review.pk];
            reviewSubject.data = review;
            (window.requestAnimationFrame||window.setTimeout)(function() {
              self.renderDecisionsUpdate(reviewSubject);
            },0);
          }
        }
        self.lastUpdate = last;
        // 4. update possible log additions
        if (changedPks.length) {
          self.loadReviewData(changedPks, function() {
            (window.requestAnimationFrame||window.setTimeout)(function() {
              for (var i=0,l=changedPks.length; i<l; i++) {
                self.renderLogUpdate(self.state[changedPks[i]]);
              }
            },0);
          });
        }
      });
  },
  initRenderAll: function() {
    for (var a in this.state) {
      var reviewSubject = this.state[a];
      if (reviewSubject.o) {
        reviewSubject.o.innerHTML = this.render(reviewSubject);
        this.postRender(reviewSubject);
      }
    }
  },
  //from scratch
  render: function(reviewSubject) {
    var self = this;
    return (''
            + '<div class="review-widget">'
            + ' <div class="row">'
            + '  <div class="col-md-10">'
            +      this.opt.schema.map(function(schema) {
                      return self.renderDecisions(schema, reviewSubject)
                   }).join('')
            + '    <div class="form-inline form-group">'
            + '      <label>Log</label><input class="log form-control" type="text" />'
            + '    </div>'
            + '  </div>'
            + '  <div class="review-header" style="padding-left:15px;">'
            + '      <button class="btn btn-default btn-primary save">Save</button>'
            + '      <span class="focus label label-info">' + this.renderFocus(reviewSubject) + '</span>'
            + '      <span class="saved label label-success"></span>' // save status
            + '  </div>'
            + ' </div>'
            + ' <div class="panel panel-default">'
            + '  <div class="panel-heading">Logs</div>'
            + '  <div class="logs panel-body" aria-labelledby="Logs" style="max-height:4em;overflow-y:scroll">'
            +      this.renderLog(reviewSubject)
            + '  </div>'
            + ' </div>'
            + '</div>'
           )
  },
  renderSaveUpdate: function(reviewSubject) {
    this.$('.saved', reviewSubject.o).html('saved!').show().fadeOut(2000);
  },
  renderLog: function(reviewSubject) {
    return ((!reviewSubject.log) ? ''
            : reviewSubject.log.map(function(log) {
              var d = new Date(log.ts * 1000);
              var dateStr = d.toLocaleDateString();
              var timeStr = d.toLocaleTimeString().replace(/:\d\d /,' ').toLowerCase();
              var tsStr = ((dateStr == new Date().toLocaleDateString()) ? timeStr : dateStr);
              return (''
                      + '<div class="logitem">'
                      + '<span class="reviewer">' + log.r + '</span>'
                      + ' (' + tsStr + '): '
                      + '<span class="logm">' + log.m + '</span>'
                      + '</div>'
                     );
              }).join(''));
  },
  renderLogUpdate: function(reviewSubject) {
    this.$('.logs', reviewSubject.o).html(this.renderLog(reviewSubject));
  },
  renderDecisions: function(schema, reviewSubject) {
    var prefix = this.prefix;
    var name = schema.name;
    return (''
            + '<div class="form-group form-inline"><label>'+schema.label+'</label> '
            + '<select class="form-control review-select-'+name+'" data-name="'+name+'" name="'+prefix+name+'_'+reviewSubject.pk+'">'
            + schema.choices.map(function(o) {
              return '<option '+(reviewSubject.data[name]==o[0]?'selected="selected"':'')+' value="'+o[0]+'">'+o[1]+'</option>';
            }).join('')
            + '</select></div>');
  },
  renderDecisionsUpdate: function(reviewSubject) {
    if (!reviewSubject.o) { throw "cannot call renderUpdate unless we have a dom object"; }
    var $ = this.$;
    this.opt.schema.map(function(schema) {
      var val = reviewSubject.data[schema.name];
      if (val) {
        $('.review-select-'+schema.name, reviewSubject.o).val(val);
      }
    });
  },
  renderFocus: function(reviewSubject) {
    return (reviewSubject.focus || '');
  },
  renderFocusUpdate: function(reviewSubject) {
    this.$('.focus', reviewSubject.o).html(this.renderFocus(reviewSubject));
  },
  postRender: function(reviewSubject) {
    var $ = this.$;
    var self = this;
    // A. any 'attention' on a review marks attention
    $('input,select', reviewSubject.o).on('click mousedown focus change', function(evt) {
      if (self.focus != reviewSubject.pk) {
        self.focus = reviewSubject.pk;
        self.postFocus(reviewSubject.pk);
      }
    });
    // B. save button listener
    $('button.save', reviewSubject.o).click(function(evt) {
      evt.preventDefault(); //disable submitting page
      // 1. get values from dom
      var reviews = {};
      $('select', reviewSubject.o).each(function() {
        var name = $(this).attr('data-name');
        var val = $(this).val();
        reviews[name] = val;
      });
      var log = $('input.log', reviewSubject.o).val().replace(/^\s+/,'').replace(/\s+$/,'');
      // 2. make sure something changed
      var changed = Boolean(log);
      for (var a in reviews) {
        if (reviewSubject.data[a] != reviews[a]) {
          reviewSubject.data[a] = reviews[a];
          changed = true;
        }
      }
      // 3. saveReview()
      if (changed) {
        self.saveReview(reviewSubject, log || undefined, function() {
          // 4. on callback: add status (and clear log message)
          self.renderSaveUpdate(reviewSubject);
          self.renderLogUpdate(reviewSubject);
          $('input.log', reviewSubject.o).val(''); //clear
        });
      }
    });
  }
};
