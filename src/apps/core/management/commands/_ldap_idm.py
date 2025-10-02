from ldap3 import Server, Connection, ALL, SIMPLE, SAFE_SYNC, AUTO_BIND_NO_TLS
import os
from dotenv import load_dotenv

load_dotenv()


class LdapIdm:
    def __init__(self):
        self.server = Server(
            os.getenv("LDAP_HOST"), port=int(os.getenv("LDAP_PORT")), use_ssl=True, get_info=ALL
        )
        self.conn = Connection(
            self.server,
            client_strategy=SAFE_SYNC,
            auto_bind=AUTO_BIND_NO_TLS,
            user=os.getenv("LDAP_BIND_DN"),
            password=os.getenv("LDAP_PASSWORD"),
            authentication=SIMPLE,
        )
        self.conn.bind()

    def get_user_service_profile(self, user_dn, project_num):
        user_set_dn = ",".join(user_dn.split(",")[1:])  # drop the user part
        user_name = user_dn.split(",")[0][3:]
        status, result, response, _ = self.conn.search(
            f"CN=SP_IDA01_{project_num}_{user_name},{user_set_dn}",
            "(objectclass=*)",
            attributes=["CSCServiceIDAQuotaGranter"],
        )
        return response[0] if status is True and len(result) > 0 else None

    def get_project_by_id(self, project_id):
        status, result, response, _ = self.conn.search(
            "OU=Projects,ou=idm,dc=csc,dc=fi",
            f"(CSCprjNum={project_id})",
            attributes=["CSCprjNum", "CSCPrjHomeOrganization", "CSCPrjPriResp"],
        )
        return response[0] if status is True and len(result) > 0 else None

    def get_org_by_id(self, org_id):
        status, result, response, _ = self.conn.search(
            "OU=Organizations,ou=idm,dc=csc,dc=fi",
            f"({org_id})",
            attributes=["schacHomeOrganization"],
        )
        return response[0] if status is True and len(result) > 0 else None

    def check_admin_org_mismatch(self, project_id):
        project = self.get_project_by_id(project_id)
        if project is None:
            return
        user_dn = project["attributes"]["CSCPrjPriResp"][0]
        user = self.get_user_service_profile(user_dn, project_id)
        if user is None:
            return
        if (
            "CSCServiceIDAQuotaGranter" in user["attributes"]
            and len(user["attributes"]["CSCServiceIDAQuotaGranter"]) > 0
        ):
            quota_granter_org_id = user["attributes"]["CSCServiceIDAQuotaGranter"][0].split(",")[0]
            org = self.get_org_by_id(quota_granter_org_id)
            if org is None:
                return
        else:
            return
        quota_granter_org = org["attributes"]["schacHomeOrganization"]
        return quota_granter_org
