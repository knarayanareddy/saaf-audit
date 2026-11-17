"use strict";

const { createCoreController } = require("@strapi/strapi").factories;

module.exports = createCoreController("api::jira-incident.jira-incident");
