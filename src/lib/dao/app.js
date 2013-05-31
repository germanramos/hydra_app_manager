var utils = require('../utils'),
enums = require('../enums');

var defaultApp = {
	appId: null,
	localStrategyEvents : {
		//'42374897239' : localStrategyEnum.INDIFFERENT
	},
	cloudStrategyEvents : {
		//'42374897239': cloudStrategyEnum.INDIFFERENT
	},
	servers : [
		//{
		//	server: 'http://server3/app',
		//	status: {
		//		cpuLoad: 50, //Cpu load of the server 0-100
		//		memLoad: 50, //Memory load of the server 0-100
		//		timeStamp: 42374897239, //UTC time stamp of this info
		//		stateEvents: {
		//			'42374897239' : state: stateEnum.READY, //Future state of the serve
		//		}
		//	}
		//}
	]
};

module.exports = function(colApp){
	var self = {};

	self.create = function(p_app, p_cbk){
		var app = utils.merge({},defaultApp);

		app = utils.merge(app, p_app);

		//Si no tenemos id no creamos la app
		if(app.appId === null){
			p_cbk(null);
			return;
		}

		colApp.insert(app, {w:1}, function(err, items){
			if(err || items.length === 0){
				p_cbk(null);
			} else {
				p_cbk(items[0]);
			}
		});
	};

	self.getAll = function(p_cbk){
		colApp.find({}).toArray(function(err, items){
			for(var i in items){
				var modified = clean(items[i]);
				if(modified) self.update(items[i]);
			}
			p_cbk(items);
		});
	};

	self.getFromId = function(p_id, p_cbk){
		var find = {
			appId: p_id
		};

		colApp.findOne(find, {}, function(err, item){
			var modified = clean(item);
			if(modified){
				self.update(item);
			}
			p_cbk(item);
		});
	};

	function clean(p_app){
		var now = new Date().getTime();

		var modified = false;

		//clean localStrategy
		var previousLocal;
		for(var local in p_app.localStrategyEvents){
			if(local < now){
				if(previousLocal > 0){
					delete p_app.localStrategyEvents[previousLocal];
					modified = true;
				}
				previousLocal = local;
			}
		}

		//clean cloudStrategy
		var previousCloud;
		for(var cloud in p_app.cloudStrategyEvents){
			if(cloud < now){
				if(previousCloud > 0){
					delete p_app.cloudStrategyEvents[previousCloud];
					modified = true;
				}
				previousCloud = cloud;
			}
		}

		//clean servers
		for(var serverIdx in p_app.servers){
			var server = p_app.servers[serverIdx];
			var previousState;
			for(var serverState in server.status.stateEvents){
				if(serverState < now){
					if(previousState > 0){
						delete server.status.stateEvents[previousState];
						modified = true;
					}
					previousState = serverState;
				}
			}
		}

		return modified;
	}

	self.update = function(p_app, p_cbk){
		var find = {
			appId: p_app.appId
		};

		colApp.findOne(find, {}, function(err, oldApp){
			p_app = utils.merge(utils.merge({},defaultApp), p_app);
			if(err || oldApp === null){
				self.create(p_app, p_cbk);
			} else {

				//merging & sort localStrategies schedule
				// merge
				for(var localStrategyEventsIdx in p_app.localStrategyEvents){
					oldApp.localStrategyEvents[localStrategyEventsIdx] = p_app.localStrategyEvents[localStrategyEventsIdx];
				}
				//sort
				oldApp.localStrategyEvents = utils.sortObj(oldApp.localStrategyEvents);

				//merging & sort cloudStrategies schedule
				//merge
				for(var cloudStrategyEventsIdx in p_app.cloudStrategyEvents){
					oldApp.cloudStrategyEvents[cloudStrategyEventsIdx] = p_app.cloudStrategyEvents[cloudStrategyEventsIdx];
				}
				//sort
				oldApp.cloudStrategyEvents = utils.sortObj(oldApp.cloudStrategyEvents);

				//merging servers
				for(var newServerIdx in p_app.servers){
					var newServer = p_app.servers[newServerIdx];

					var serverFound = false;
					for(var oldServerIdx in oldApp.servers){
						var oldServer = oldApp.servers[oldServerIdx];
						if(newServer.server == oldServer.server){
							for(var stateEventsIdx in newServer.status.stateEvents){
								oldServer.status.stateEvents[stateEventsIdx] = newServer.status.stateEvents[stateEventsIdx];
							}
							oldServer.status.stateEvents = utils.sortObj(oldServer.status.stateEvents);

							// Checks timestamp for cpu/mem updates
							if(newServer.status.timeStamp > oldServer.status.timeStamp){
								for(var serverStatusFieldIdx in newServer.status){
									if(serverStatusFieldIdx == 'stateEvents') continue;
									oldServer.status[serverStatusFieldIdx] = newServer.status[serverStatusFieldIdx];
								}
							}

							found = true;
							break;
						}
					}
					if(!found) {
						oldApp.servers.push(newServer);
					}

				}

				clean(oldApp);

				colApp.update(find, oldApp, function(err){
					if(p_cbk) p_cbk();
				});
			}
		});
	};

	self.remove = function(p_id, p_cbk){
		var find = {
			appId: p_id
		};

		colApp.remove(find, function(err, item){
			if(err) {
				p_cbk(err);
			}
			else {
				p_cbk(null);
			}
		});
	};

	return self;
};
