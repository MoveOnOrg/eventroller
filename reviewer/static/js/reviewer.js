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
    var subject = $(widget).attr('data-subject');
    if (!(this.state[pk])) {
      this.state[pk] = {'pk': pk,
                        'subject': subject || undefined,
                        'o': widget,
                        'data': null,
                        'focus': []};
    }
  },
  updateMissingData: function(callback) {
    var newPks = [];
    var subjects = [];
    for (var a in this.state) {
      if (!this.state[a].data) {
        newPks.push(a);
        subjects.push(this.state[a].subject);
      }
    }
    this.loadReviewData(newPks, callback, subjects);
  },
  loadReviewData: function(pks, callback, subjects) {
    var self = this;
    var useSubjects = (subjects || []).filter(function(x){return x}).length;
    this.$.getJSON(this.opt.apiPath + '/history/' + this.opt.organization
                   + '/?logs=1&type=' + this.opt.contentType
                   + '&pks=' + pks.join(',')
                   + ((useSubjects) ? '&subjects=' + subjects.join(',') : '')
                  )
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
          callback(pks, data);
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
    var csrfmiddlewaretoken = $('input[name=csrfmiddlewaretoken]').val();
    this.$.ajax({
      'url': (opt.apiPath + ['', opt.organization, opt.contentType, reviewSubject.pk, ''].join('/')),
      'method': 'POST',
      'data': {
        csrfmiddlewaretoken: csrfmiddlewaretoken,
        content_type: opt.contentType,
        pk: reviewSubject.pk,
        decisions: decisions.join(';'),
        log: log,
        subject: reviewSubject.subject
      }
    }).then(function() {
      if (log) {
        if (!reviewSubject.log) { reviewSubject.log = []; }
        reviewSubject.log.unshift({"m":log,
                         "r":'<i>me</i>',
                         "pk": reviewSubject.pk,
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
            if (f[1] in newFocus) {
              newFocus[f[1]].push(f[2]);
              newFocus[f[1]].sort(); //make sure the order is consistent
            } else {
              newFocus[f[1]] = [ f[2] ];
            }
          }
        }
        // 2. update focus dom
        (window.requestAnimationFrame||window.setTimeout)(function() {
          var oldFocus = self.focus;
          self.focus = newFocus;
          // not just update new focii, but clear old
          for (var pk in self.state) {
            if (pk in newFocus) {
              //dumbest, but easiest way to compare lists
              if (newFocus[pk].toString() != self.state[pk].focus.toString()) {
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
            (window.requestAnimationFrame||window.setTimeout)(function(updatedPks) {
              for (var i=0,l=updatedPks.length; i<l; i++) {
                self.renderLogUpdate(self.state[updatedPks[i]]);
              }
            },0);
          });
        }
      });
  },
  initRenderAll: function(pks) {
    if (!pks) {
      pks = Object.keys(this.state);
    }
    for (var i=0,l=pks.length; i<l; i++) {
      var reviewSubject = this.state[pks[i]];
      if (reviewSubject.o && reviewSubject.data) {
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
            + '      <label>Note </label> <input class="log form-control" type="text" />'
            + '    </div>'
            + '  </div>'
            + '  <div class="review-header" style="padding-left:15px;">'
            + '      <button class="btn btn-default btn-primary save">Save</button>'
            + '      <span class="focus">' + this.renderFocus(reviewSubject) + '</span>'
            + '      <span class="saved label label-success"></span>' // save status
            + '  </div>'
            + ' </div>'
            + ' <b>Notes:</b>'
            + ' <div class="logs well well-sm" aria-labelledby="Notes" style="max-height:7em;overflow-y:scroll">'
            +      this.renderLog(reviewSubject)
            + ' </div>'
            + '</div>'
           )
  },
  renderSaveUpdate: function(reviewSubject) {
    this.$('.saved', reviewSubject.o).html('saved!').show().fadeOut(2000);
  },
  renderLog: function(reviewSubject) {
    if (!reviewSubject.log || !reviewSubject.log.length) {
      return '';
    }
    var isHostLog = function(log) {
      return (reviewSubject.pk != log.pk);
    }
    var renderLogHtml = function(log) {
      var d = new Date(log.ts * 1000);
      var dateStr = d.toLocaleDateString();
      var timeStr = d.toLocaleTimeString().replace(/:\d\d /,' ').toLowerCase();
      var tsStr = ((dateStr == new Date().toLocaleDateString()) ? timeStr : dateStr);
      var other = isHostLog(log);
      var hue = 10*(parseInt(log.pk||0) % 36);
      return (''
              + '<div class="logitem"'
              + ((other && log.pk) ? ' data-pk="'+log.pk+'" style="background-color: hsl('+hue+',17%,80%)"' : '')
              + '>'
              + ((other && log.pk) ? '-- ' : '')
              + '<span class="reviewer">' + log.r + '</span>'
              + ' (' + tsStr + '): '
              + '<span class="logm">' + log.m + '</span>'
              + '</div>'
             );
    };
    var eventNotes = '';
    var hostNotes = '';
    reviewSubject.log.map(function(log) {
      if (isHostLog(log)) {
        hostNotes = hostNotes + renderLogHtml(log);
      } else {
        eventNotes = eventNotes + renderLogHtml(log);
      }
    });
    if (hostNotes) {
      eventNotes = eventNotes + '<div><b>Host Notes (from past events)</b></div>' + hostNotes;
    }
    return eventNotes

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
    if (!reviewSubject.focus || !reviewSubject.focus.length) {
      return '';
    }
    return reviewSubject.focus.map(function(reviewer) {
      return '<span class="label label-info">'+reviewer+'</span>'
    }).join('');
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
