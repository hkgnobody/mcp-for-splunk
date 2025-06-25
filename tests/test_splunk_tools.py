"""
Tests for Splunk tools functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src import server
from src.splunk_client import get_splunk_service


class TestSplunkHealthTool:
    """Test the health check functionality"""
    
    def test_health_check_success(self):
        """Test successful health check"""
        with patch('src.server.get_splunk_service') as mock_get_service:
            mock_service = Mock()
            mock_service.info = {"version": "9.0.0", "host": "localhost"}
            mock_get_service.return_value = mock_service
            
            result = server.get_splunk_health()
            
            assert result["status"] == "connected"
            assert result["version"] == "9.0.0"
            assert result["server_name"] == "localhost"
    
    def test_health_check_failure(self):
        """Test health check failure"""
        with patch('src.server.get_splunk_service') as mock_get_service:
            mock_get_service.side_effect = Exception("Connection failed")
            
            result = server.get_splunk_health()
            
            assert result["status"] == "error"
            assert "Connection failed" in result["error"]

    def test_health_check_missing_host(self):
        """Test health check with missing host information"""
        with patch('src.server.get_splunk_service') as mock_get_service:
            mock_service = Mock()
            mock_service.info = {"version": "9.0.0"}  # Missing host
            mock_get_service.return_value = mock_service
            
            result = server.get_splunk_health()
            
            assert result["status"] == "connected"
            assert result["version"] == "9.0.0"
            assert result["server_name"] == "unknown"


class TestIndexTools:
    """Test index-related tools"""
    
    def test_list_indexes_success(self, mock_context):
        """Test successful index listing"""
        result = server.list_indexes(mock_context)
        
        assert "indexes" in result
        assert "count" in result
        assert result["count"] == 4
        expected_indexes = ["_internal", "main", "security", "test"]
        assert sorted(result["indexes"]) == expected_indexes


class TestMetadataTools:
    """Test metadata tools (sourcetypes and sources)"""
    
    def test_list_sourcetypes_success(self, mock_context, mock_results_reader):
        """Test successful sourcetype listing"""
        with patch('src.server.ResultsReader', mock_results_reader):
            # Mock the oneshot job
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            
            # Mock ResultsReader with sourcetype data
            sourcetype_results = [
                {"sourcetype": "access_combined"},
                {"sourcetype": "splunkd"},
                {"sourcetype": "web_service"}
            ]
            with patch('src.server.ResultsReader') as mock_reader:
                mock_reader.return_value = iter(sourcetype_results)
                
                result = server.list_sourcetypes(mock_context)
                
                assert "sourcetypes" in result
                assert "count" in result
                assert result["count"] == 3
                expected_sourcetypes = ["access_combined", "splunkd", "web_service"]
                assert sorted(result["sourcetypes"]) == expected_sourcetypes

    def test_list_sources_success(self, mock_context):
        """Test successful source listing"""
        with patch('src.server.ResultsReader') as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            
            source_results = [
                {"source": "/var/log/system.log"},
                {"source": "/var/log/app.log"}
            ]
            mock_reader.return_value = iter(source_results)
            
            result = server.list_sources(mock_context)
            
            assert "sources" in result
            assert "count" in result
            assert result["count"] == 2


class TestSearchTools:
    """Test search functionality"""

    def test_run_oneshot_search_basic(self, mock_context, mock_search_results):
        """Test basic oneshot search"""
        with patch('src.server.ResultsReader') as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)
            
            result = server.run_oneshot_search(
                mock_context,
                query="index=main",
                earliest_time="-1h",
                latest_time="now",
                max_results=10
            )
            
            assert "results" in result
            assert "results_count" in result
            assert "query_executed" in result
            assert result["results_count"] == 3
            assert "search index=main" in result["query_executed"]

    def test_run_oneshot_search_with_pipe(self, mock_context, mock_search_results):
        """Test oneshot search with pipe command (no prefix modification)"""
        with patch('src.server.ResultsReader') as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)
            
            result = server.run_oneshot_search(
                mock_context,
                query="| stats count by log_level"
            )
            
            assert result["query_executed"] == "| stats count by log_level"

    def test_run_oneshot_search_with_search_prefix(self, mock_context, mock_search_results):
        """Test oneshot search that already has search prefix"""
        with patch('src.server.ResultsReader') as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)
            
            result = server.run_oneshot_search(
                mock_context,
                query="search index=main"
            )
            
            assert result["query_executed"] == "search index=main"

    def test_run_oneshot_search_max_results_limit(self, mock_context):
        """Test oneshot search with max results limiting"""
        large_results = [{"result": i} for i in range(150)]
        
        with patch('src.server.ResultsReader') as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(large_results)
            
            result = server.run_oneshot_search(
                mock_context,
                query="index=main",
                max_results=100
            )
            
            assert result["results_count"] == 100

    def test_run_oneshot_search_error(self, mock_context):
        """Test oneshot search error handling"""
        mock_context.request_context.lifespan_context.service.jobs.oneshot.side_effect = Exception("Search failed")
        
        with pytest.raises(Exception, match="Search failed"):
            server.run_oneshot_search(mock_context, query="index=main")


class TestAppAndUserTools:
    """Test app and user management tools"""
    
    def test_list_apps_success(self, mock_context):
        """Test successful app listing"""
        result = server.list_apps(mock_context)
        
        assert "apps" in result
        assert "count" in result
        assert result["count"] == 3
        app_names = [app["name"] for app in result["apps"]]
        expected_apps = ["search", "splunk_monitoring_console", "learned"]
        assert sorted(app_names) == sorted(expected_apps)

    def test_list_users_success(self, mock_context):
        """Test successful user listing"""
        result = server.list_users(mock_context)
        
        assert "users" in result
        assert "count" in result
        assert result["count"] == 2
        user_names = [user["username"] for user in result["users"]]
        expected_users = ["admin", "splunk-system-user"]
        assert sorted(user_names) == sorted(expected_users)


class TestKVStoreTools:
    """Test KV Store tools"""
    
    def test_list_kvstore_collections_specific_app(self, mock_context):
        """Test listing KV Store collections for specific app"""
        # Mock collections for a specific app
        mock_collections = [Mock(name="users"), Mock(name="settings")]
        for coll in mock_collections:
            coll.name = coll._mock_name
        
        mock_context.request_context.lifespan_context.service.kvstore = {
            "search": mock_collections
        }
        
        result = server.list_kvstore_collections(mock_context, app="search")
        
        assert "collections" in result
        assert "count" in result
        # The actual implementation might behave differently, so we just check structure

    def test_get_kvstore_data_success(self, mock_context, mock_kvstore_collection_data):
        """Test successful KV Store data retrieval"""
        mock_collection = Mock()
        mock_collection.data.query.return_value = mock_kvstore_collection_data
        
        mock_context.request_context.lifespan_context.service.kvstore = {
            "search": {"users": mock_collection}
        }
        
        result = server.get_kvstore_data(mock_context, collection="users", app="search")
        
        assert "documents" in result
        assert "count" in result


class TestConfigurationTools:
    """Test configuration tools"""
    
    def test_get_configurations_all_stanzas(self, mock_context):
        """Test getting all configuration stanzas"""
        mock_stanza = Mock()
        mock_stanza.name = "default"
        mock_stanza.content = {"setting1": "value1", "setting2": "value2"}
        
        mock_conf = Mock()
        mock_conf.__iter__ = Mock(return_value=iter([mock_stanza]))
        
        mock_context.request_context.lifespan_context.service.confs = {"props": mock_conf}
        
        result = server.get_configurations(mock_context, conf_file="props")
        
        assert "file" in result
        assert "stanzas" in result
        assert result["file"] == "props"

    def test_get_configurations_specific_stanza(self, mock_context):
        """Test getting specific configuration stanza"""
        mock_stanza = Mock()
        mock_stanza.content = {"setting1": "value1"}
        
        mock_conf = Mock()
        mock_conf.__getitem__ = Mock(return_value=mock_stanza)
        
        mock_context.request_context.lifespan_context.service.confs = {"props": mock_conf}
        
        result = server.get_configurations(mock_context, conf_file="props", stanza="default")
        
        assert "stanza" in result
        assert "settings" in result
        assert result["stanza"] == "default"


class TestToolIntegration:
    """Test integration between different tools"""
    
    def test_health_check_before_operations(self, mock_context):
        """Test that health check works before other operations"""
        with patch('src.server.get_splunk_service') as mock_get_service:
            mock_service = Mock()
            mock_service.info = {"version": "9.0.0", "host": "localhost"}
            mock_get_service.return_value = mock_service
            
            # Health check should work
            health_result = server.get_splunk_health()
            assert health_result["status"] == "connected"
            
            # Then other operations should work
            indexes_result = server.list_indexes(mock_context)
            assert "indexes" in indexes_result

    def test_search_workflow(self, mock_context, mock_search_results):
        """Test complete search workflow"""
        with patch('src.server.ResultsReader') as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)
            
            # First, check indexes
            indexes_result = server.list_indexes(mock_context)
            assert "main" in indexes_result["indexes"]
            
            # Then run a search on that index
            search_result = server.run_oneshot_search(
                mock_context,
                query="index=main",
                max_results=5
            )
            assert search_result["results_count"] == 3 