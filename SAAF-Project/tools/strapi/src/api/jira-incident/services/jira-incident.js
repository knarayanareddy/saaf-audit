"use strict";

const { createCoreService } = require("@strapi/strapi").factories;

module.exports = createCoreService("api::jira-incident.jira-incident");
