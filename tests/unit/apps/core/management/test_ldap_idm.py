import os
from unittest.mock import Mock, patch, MagicMock
import pytest
from ldap3 import Server, Connection, ALL, SIMPLE, SAFE_SYNC, AUTO_BIND_NO_TLS

from apps.core.management.commands._ldap_idm import LdapIdm


class TestLdapIdm:
    """Test cases for LdapIdm class."""

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_init_success(self, mock_connection_class, mock_server_class):
        """Test successful LdapIdm initialization."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Verify Server was created with correct parameters
        mock_server_class.assert_called_once_with(
            "test.ldap.com", port=636, use_ssl=True, get_info=ALL
        )

        # Verify Connection was created with correct parameters
        mock_connection_class.assert_called_once_with(
            mock_server,
            client_strategy=SAFE_SYNC,
            auto_bind=AUTO_BIND_NO_TLS,
            user="cn=admin,dc=test,dc=com",
            password="testpassword",
            authentication=SIMPLE,
        )

        # Verify bind was called
        mock_conn.bind.assert_called_once()

        # Verify instance attributes
        assert ldap_idm.server == mock_server
        assert ldap_idm.conn == mock_conn

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "invalid_port",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_init_invalid_port(self, mock_connection_class, mock_server_class):
        """Test LdapIdm initialization with invalid port."""
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Should raise ValueError for invalid port
        with pytest.raises(ValueError):
            LdapIdm()

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_user_service_profile_success(self, mock_connection_class, mock_server_class):
        """Test successful get_user_service_profile call."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock successful search response
        mock_response = [
            {"attributes": {"CSCServiceIDAQuotaGranter": ["test-org-id,ou=orgs,dc=test,dc=com"]}}
        ]
        mock_conn.search.return_value = (True, [1], mock_response, None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test get_user_service_profile
        user_dn = "uid=testuser,ou=users,dc=test,dc=com"
        project_num = "2001479"
        result = ldap_idm.get_user_service_profile(user_dn, project_num)

        # Verify search was called with correct parameters
        expected_search_dn = "CN=SP_IDA01_2001479_=testuser,ou=users,dc=test,dc=com"
        mock_conn.search.assert_called_once_with(
            expected_search_dn, "(objectclass=*)", attributes=["CSCServiceIDAQuotaGranter"]
        )

        # Verify result
        assert result == mock_response[0]

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_user_service_profile_not_found(self, mock_connection_class, mock_server_class):
        """Test get_user_service_profile when user is not found."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock unsuccessful search response
        mock_conn.search.return_value = (False, 0, [], None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test get_user_service_profile
        user_dn = "uid=testuser,ou=users,dc=test,dc=com"
        project_num = "2001479"
        result = ldap_idm.get_user_service_profile(user_dn, project_num)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_project_by_id_success(self, mock_connection_class, mock_server_class):
        """Test successful get_project_by_id call."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock successful search response
        mock_response = [
            {
                "attributes": {
                    "CSCprjNum": ["2001479"],
                    "CSCPrjHomeOrganization": ["test-org"],
                    "CSCPrjPriResp": ["uid=testuser,ou=users,dc=test,dc=com"],
                }
            }
        ]
        mock_conn.search.return_value = (True, [1], mock_response, None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test get_project_by_id
        project_id = "2001479"
        result = ldap_idm.get_project_by_id(project_id)

        # Verify search was called with correct parameters
        mock_conn.search.assert_called_once_with(
            "OU=Projects,ou=idm,dc=csc,dc=fi",
            "(CSCprjNum=2001479)",
            attributes=["CSCprjNum", "CSCPrjHomeOrganization", "CSCPrjPriResp"],
        )

        # Verify result
        assert result == mock_response[0]

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_project_by_id_not_found(self, mock_connection_class, mock_server_class):
        """Test get_project_by_id when project is not found."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock unsuccessful search response
        mock_conn.search.return_value = (False, 0, [], None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test get_project_by_id
        project_id = "9999999"
        result = ldap_idm.get_project_by_id(project_id)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_org_by_id_success(self, mock_connection_class, mock_server_class):
        """Test successful get_org_by_id call."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock successful search response
        mock_response = [{"attributes": {"schacHomeOrganization": ["test-org.fi"]}}]
        mock_conn.search.return_value = (True, [1], mock_response, None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test get_org_by_id
        org_id = "test-org-id"
        result = ldap_idm.get_org_by_id(org_id)

        # Verify search was called with correct parameters
        mock_conn.search.assert_called_once_with(
            "OU=Organizations,ou=idm,dc=csc,dc=fi",
            "(test-org-id)",
            attributes=["schacHomeOrganization"],
        )

        # Verify result
        assert result == mock_response[0]

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_org_by_id_not_found(self, mock_connection_class, mock_server_class):
        """Test get_org_by_id when organization is not found."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock unsuccessful search response
        mock_conn.search.return_value = (False, 0, [], None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test get_org_by_id
        org_id = "unknown-org-id"
        result = ldap_idm.get_org_by_id(org_id)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_check_admin_org_mismatch_success(self, mock_connection_class, mock_server_class):
        """Test successful check_admin_org_mismatch call."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Mock project data
        project_data = {"attributes": {"CSCPrjPriResp": ["uid=testuser,ou=users,dc=test,dc=com"]}}

        # Mock user service profile data
        user_data = {
            "attributes": {"CSCServiceIDAQuotaGranter": ["test-org-id,ou=orgs,dc=test,dc=com"]}
        }

        # Mock organization data
        org_data = {"attributes": {"schacHomeOrganization": ["test-org.fi"]}}

        # Mock search responses
        def mock_search_side_effect(search_base, search_filter, attributes):
            if "OU=Projects" in search_base:
                return (True, [1], [project_data], None)
            elif "CN=SP_IDA01" in search_base:
                return (True, [1], [user_data], None)
            elif "OU=Organizations" in search_base:
                return (True, [1], [org_data], None)
            else:
                return (False, [], [], None)

        mock_conn.search.side_effect = mock_search_side_effect

        # Test check_admin_org_mismatch
        project_id = "2001479"
        result = ldap_idm.check_admin_org_mismatch(project_id)

        # Verify result
        assert result == ["test-org.fi"]

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_check_admin_org_mismatch_project_not_found(
        self, mock_connection_class, mock_server_class
    ):
        """Test check_admin_org_mismatch when project is not found."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock unsuccessful project search
        mock_conn.search.return_value = (False, 0, [], None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test check_admin_org_mismatch
        project_id = "9999999"
        result = ldap_idm.check_admin_org_mismatch(project_id)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_check_admin_org_mismatch_user_not_found(
        self, mock_connection_class, mock_server_class
    ):
        """Test check_admin_org_mismatch when user service profile is not found."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock project data
        project_data = {"attributes": {"CSCPrjPriResp": ["uid=testuser,ou=users,dc=test,dc=com"]}}

        # Mock search responses
        def mock_search_side_effect(search_base, search_filter, attributes):
            if "OU=Projects" in search_base:
                return (True, [1], [project_data], None)
            else:
                return (False, [], [], None)

        mock_conn.search.side_effect = mock_search_side_effect

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test check_admin_org_mismatch
        project_id = "2001479"
        result = ldap_idm.check_admin_org_mismatch(project_id)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_check_admin_org_mismatch_no_quota_granter(
        self, mock_connection_class, mock_server_class
    ):
        """Test check_admin_org_mismatch when user has no quota granter."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock project data
        project_data = {"attributes": {"CSCPrjPriResp": ["uid=testuser,ou=users,dc=test,dc=com"]}}

        # Mock user service profile data without quota granter
        user_data = {"attributes": {}}

        # Mock search responses
        def mock_search_side_effect(search_base, search_filter, attributes):
            if "OU=Projects" in search_base:
                return (True, [1], [project_data], None)
            elif "CN=SP_IDA01" in search_base:
                return (True, [1], [user_data], None)
            else:
                return (False, [], [], None)

        mock_conn.search.side_effect = mock_search_side_effect

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test check_admin_org_mismatch
        project_id = "2001479"
        result = ldap_idm.check_admin_org_mismatch(project_id)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_check_admin_org_mismatch_org_not_found(
        self, mock_connection_class, mock_server_class
    ):
        """Test check_admin_org_mismatch when organization is not found."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock project data
        project_data = {"attributes": {"CSCPrjPriResp": ["uid=testuser,ou=users,dc=test,dc=com"]}}

        # Mock user service profile data
        user_data = {
            "attributes": {"CSCServiceIDAQuotaGranter": ["test-org-id,ou=orgs,dc=test,dc=com"]}
        }

        # Mock search responses
        def mock_search_side_effect(search_base, search_filter, attributes):
            if "OU=Projects" in search_base:
                return (True, [1], [project_data], None)
            elif "CN=SP_IDA01" in search_base:
                return (True, [1], [user_data], None)
            else:
                return (False, [], [], None)

        mock_conn.search.side_effect = mock_search_side_effect

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test check_admin_org_mismatch
        project_id = "2001479"
        result = ldap_idm.check_admin_org_mismatch(project_id)

        # Verify result is None
        assert result is None

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_get_user_service_profile_dn_parsing(self, mock_connection_class, mock_server_class):
        """Test get_user_service_profile with different DN formats."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_connection_class.return_value = mock_conn

        # Mock successful search response
        mock_response = [
            {"attributes": {"CSCServiceIDAQuotaGranter": ["test-org-id,ou=orgs,dc=test,dc=com"]}}
        ]
        mock_conn.search.return_value = (True, [1], mock_response, None)

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test with different DN formats
        test_cases = [
            (
                "uid=testuser,ou=users,dc=test,dc=com",
                "2001479",
                "CN=SP_IDA01_2001479_=testuser,ou=users,dc=test,dc=com",
            ),
            (
                "cn=testuser,ou=users,dc=test,dc=com",
                "2001479",
                "CN=SP_IDA01_2001479_testuser,ou=users,dc=test,dc=com",
            ),
            (
                "uid=testuser,ou=users,dc=test,dc=com",
                "123456",
                "CN=SP_IDA01_123456_=testuser,ou=users,dc=test,dc=com",
            ),
        ]

        for user_dn, project_num, expected_search_dn in test_cases:
            # Reset mock for each test case
            mock_conn.reset_mock()

            # Test get_user_service_profile
            result = ldap_idm.get_user_service_profile(user_dn, project_num)

            # Verify search was called with correct parameters
            mock_conn.search.assert_called_once_with(
                expected_search_dn, "(objectclass=*)", attributes=["CSCServiceIDAQuotaGranter"]
            )

            # Verify result
            assert result == mock_response[0]

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_connection_bind_failure(self, mock_connection_class, mock_server_class):
        """Test LdapIdm initialization when connection bind fails."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_conn.bind.side_effect = Exception("Connection failed")
        mock_connection_class.return_value = mock_conn

        # Should raise the exception from bind
        with pytest.raises(Exception, match="Connection failed"):
            LdapIdm()

    @patch.dict(
        os.environ,
        {
            "LDAP_HOST": "test.ldap.com",
            "LDAP_PORT": "636",
            "LDAP_BIND_DN": "cn=admin,dc=test,dc=com",
            "LDAP_PASSWORD": "testpassword",
        },
    )
    @patch("apps.core.management.commands._ldap_idm.Server")
    @patch("apps.core.management.commands._ldap_idm.Connection")
    def test_search_exception_handling(self, mock_connection_class, mock_server_class):
        """Test exception handling in search methods."""
        # Setup mocks
        mock_server = Mock()
        mock_server_class.return_value = mock_server

        mock_conn = Mock()
        mock_conn.search.side_effect = Exception("Search failed")
        mock_connection_class.return_value = mock_conn

        # Create LdapIdm instance
        ldap_idm = LdapIdm()

        # Test that exceptions are propagated
        with pytest.raises(Exception, match="Search failed"):
            ldap_idm.get_project_by_id("2001479")

        with pytest.raises(Exception, match="Search failed"):
            ldap_idm.get_org_by_id("test-org-id")

        with pytest.raises(Exception, match="Search failed"):
            ldap_idm.get_user_service_profile("uid=testuser,ou=users,dc=test,dc=com", "2001479")
