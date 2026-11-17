"use strict";

const ADMIN_EMAIL =
  process.env.SAAF_STRAPI_ADMIN_EMAIL ||
  process.env.STRAPI_ADMIN_EMAIL ||
  "admin@example.com";
const ADMIN_PASSWORD =
  process.env.SAAF_STRAPI_ADMIN_PASSWORD ||
  process.env.STRAPI_ADMIN_PASSWORD ||
  "ChangeMe123!";

const CONTENT_TYPES = [
  "api::jira-incident.jira-incident",
  "api::access-review.access-review",
  "api::change-ticket.change-ticket",
  "api::vendor-contract.vendor-contract",
  "api::audit-finding.audit-finding",
];

async function ensurePublicReadPermissions(strapi) {
  const role = await strapi
    .query("plugin::users-permissions.role")
    .findOne({ where: { type: "public" } });

  if (!role) {
    strapi.log.warn("Public role not found; skipping permission bootstrap.");
    return;
  }

  const permissionQuery = strapi.query("plugin::users-permissions.permission");

  for (const action of ["find", "findOne"]) {
    for (const contentType of CONTENT_TYPES) {
      const existing = await permissionQuery.findOne({
        where: {
          role: role.id,
          action: `${contentType}.${action}`,
        },
      });

      if (existing && existing.enabled) {
        continue;
      }

      if (existing) {
        await permissionQuery.update({
          where: { id: existing.id },
          data: { enabled: true },
        });
        continue;
      }

      await permissionQuery.create({
        data: {
          action: `${contentType}.${action}`,
          role: role.id,
          enabled: true,
        },
      });
    }
  }
}

async function ensureAdminUser(strapi) {
  const existingAdmin = await strapi.db.query("admin::user").findOne({
    where: { email: ADMIN_EMAIL },
  });

  if (existingAdmin) {
    return;
  }

  const superAdminRole = await strapi.admin.services.role.getSuperAdmin();
  const hashedPassword = await strapi.admin.services.auth.hashPassword(ADMIN_PASSWORD);

  await strapi.db.query("admin::user").create({
    data: {
      firstname: "SAAF",
      lastname: "Admin",
      username: "saaf-admin",
      email: ADMIN_EMAIL,
      password: hashedPassword,
      isActive: true,
      blocked: false,
      preferedLanguage: "en",
      roles: [superAdminRole.id],
    },
  });
}

module.exports = {
  async bootstrap({ strapi }) {
    await ensureAdminUser(strapi);
    await ensurePublicReadPermissions(strapi);
  },
};
