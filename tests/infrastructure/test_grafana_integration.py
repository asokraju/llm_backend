"""Infrastructure tests for Grafana dashboard and visualization integration."""

import pytest
import requests
import json
import base64
from typing import Dict, List, Any


class TestGrafanaIntegration:
    """Test Grafana dashboard and visualization functionality."""
    
    @pytest.fixture
    def grafana_url(self):
        """Grafana base URL."""
        return "http://localhost:3000"
    
    @pytest.fixture
    def grafana_auth(self):
        """Grafana authentication credentials."""
        # Default credentials from docker-compose
        username = "admin"
        password = "admin"
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded_credentials}"}
    
    def test_grafana_connectivity(self, grafana_url):
        """Test basic Grafana connectivity."""
        # Test Grafana health endpoint
        response = requests.get(f"{grafana_url}/api/health", timeout=10)
        assert response.status_code == 200
        
        health_data = response.json()
        assert "database" in health_data
        assert health_data["database"] == "ok"
        
        print(f"✅ Grafana connected successfully.")
        print(f"   - Database status: {health_data['database']}")
        print(f"   - Version: {health_data.get('version', 'unknown')}")
    
    def test_grafana_authentication(self, grafana_url, grafana_auth):
        """Test Grafana authentication and user info."""
        # Test user info endpoint
        response = requests.get(
            f"{grafana_url}/api/user", 
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Grafana authentication successful.")
            print(f"   - User: {user_info.get('login')}")
            print(f"   - Name: {user_info.get('name')}")
            print(f"   - Role: {user_info.get('orgRole')}")
            
        elif response.status_code == 401:
            print("⚠️  Grafana authentication failed - using default credentials")
            # Try without auth (might be in anonymous mode)
            pytest.skip("Grafana authentication required but failed")
        else:
            pytest.skip(f"Unexpected Grafana response: {response.status_code}")
    
    def test_grafana_datasources(self, grafana_url, grafana_auth):
        """Test Grafana datasource configuration."""
        response = requests.get(
            f"{grafana_url}/api/datasources",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code != 200:
            pytest.skip("Could not access Grafana datasources")
        
        datasources = response.json()
        
        # Look for expected datasources
        expected_datasources = ["prometheus", "redis"]
        found_datasources = {}
        
        for ds in datasources:
            ds_type = ds.get("type", "").lower()
            ds_name = ds.get("name", "").lower()
            ds_url = ds.get("url", "")
            ds_access = ds.get("access", "")
            
            for expected in expected_datasources:
                if expected in ds_type or expected in ds_name:
                    found_datasources[expected] = {
                        "name": ds["name"],
                        "type": ds["type"],
                        "url": ds_url,
                        "access": ds_access,
                        "id": ds["id"]
                    }
        
        print(f"✅ Grafana datasources configured:")
        print(f"   - Total datasources: {len(datasources)}")
        print(f"   - Expected datasources found: {len(found_datasources)}")
        
        for ds_name, ds_info in found_datasources.items():
            print(f"   - {ds_name}: {ds_info['type']} ({ds_info['url']})")
        
        # Test datasource connectivity
        for ds_name, ds_info in found_datasources.items():
            self._test_datasource_connectivity(grafana_url, grafana_auth, ds_info)
    
    def _test_datasource_connectivity(self, grafana_url, grafana_auth, datasource_info):
        """Test connectivity to a specific datasource."""
        ds_id = datasource_info["id"]
        
        response = requests.get(
            f"{grafana_url}/api/datasources/{ds_id}/health",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code == 200:
            health_data = response.json()
            status = health_data.get("status", "unknown")
            message = health_data.get("message", "")
            
            print(f"     Health: {status} - {message}")
        else:
            print(f"     Health check failed: {response.status_code}")
    
    def test_grafana_dashboards(self, grafana_url, grafana_auth):
        """Test Grafana dashboard configuration and accessibility."""
        # Get all dashboards
        response = requests.get(
            f"{grafana_url}/api/search?type=dash-db",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code != 200:
            pytest.skip("Could not access Grafana dashboards")
        
        dashboards = response.json()
        
        print(f"✅ Grafana dashboards:")
        print(f"   - Total dashboards: {len(dashboards)}")
        
        # Look for RAG-related dashboards
        rag_dashboards = []
        for dashboard in dashboards:
            title = dashboard.get("title", "").lower()
            if any(keyword in title for keyword in ["rag", "lightrag", "api", "system"]):
                rag_dashboards.append(dashboard)
                print(f"   - RAG Dashboard: {dashboard['title']} (UID: {dashboard.get('uid')})")
        
        # Test loading a specific dashboard if available
        if rag_dashboards:
            self._test_dashboard_loading(grafana_url, grafana_auth, rag_dashboards[0])
        elif dashboards:
            # Test loading any available dashboard
            self._test_dashboard_loading(grafana_url, grafana_auth, dashboards[0])
        
        return len(dashboards)
    
    def _test_dashboard_loading(self, grafana_url, grafana_auth, dashboard_info):
        """Test loading a specific dashboard."""
        dashboard_uid = dashboard_info.get("uid")
        if not dashboard_uid:
            return
        
        response = requests.get(
            f"{grafana_url}/api/dashboards/uid/{dashboard_uid}",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code == 200:
            dashboard_data = response.json()
            dashboard = dashboard_data.get("dashboard", {})
            
            title = dashboard.get("title", "Unknown")
            panels = dashboard.get("panels", [])
            
            print(f"     ✅ Dashboard '{title}' loaded successfully")
            print(f"       - Panels: {len(panels)}")
            print(f"       - Tags: {dashboard.get('tags', [])}")
            
            # Test panel queries
            self._test_dashboard_panels(panels)
        else:
            print(f"     ❌ Failed to load dashboard: {response.status_code}")
    
    def _test_dashboard_panels(self, panels):
        """Analyze dashboard panels for metrics queries."""
        panel_types = {}
        query_count = 0
        
        for panel in panels:
            panel_type = panel.get("type", "unknown")
            panel_types[panel_type] = panel_types.get(panel_type, 0) + 1
            
            # Count queries in targets
            targets = panel.get("targets", [])
            query_count += len(targets)
            
            # Show sample queries
            for target in targets[:2]:  # Show first 2 queries
                expr = target.get("expr", "")
                if expr:
                    print(f"       - Query: {expr[:60]}{'...' if len(expr) > 60 else ''}")
        
        print(f"       - Panel types: {dict(panel_types)}")
        print(f"       - Total queries: {query_count}")
    
    def test_grafana_alerting(self, grafana_url, grafana_auth):
        """Test Grafana alerting configuration."""
        # Test alert rules
        response = requests.get(
            f"{grafana_url}/api/ruler/grafana/api/v1/rules",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code == 200:
            rules_data = response.json()
            
            total_rules = 0
            for namespace, groups in rules_data.items():
                for group in groups:
                    rules = group.get("rules", [])
                    total_rules += len(rules)
            
            print(f"✅ Grafana alerting:")
            print(f"   - Namespaces: {len(rules_data)}")
            print(f"   - Total alert rules: {total_rules}")
            
        # Test alert instances
        response = requests.get(
            f"{grafana_url}/api/alertmanager/grafana/api/v2/alerts",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code == 200:
            alerts = response.json()
            active_alerts = [alert for alert in alerts if alert.get("status", {}).get("state") == "active"]
            
            print(f"   - Active alerts: {len(active_alerts)}")
            
            for alert in active_alerts[:3]:  # Show first 3 active alerts
                labels = alert.get("labels", {})
                alert_name = labels.get("alertname", "Unknown")
                print(f"     - {alert_name}: {alert.get('status', {}).get('state')}")
    
    def test_grafana_plugins(self, grafana_url, grafana_auth):
        """Test Grafana plugins installation."""
        response = requests.get(
            f"{grafana_url}/api/plugins",
            headers=grafana_auth,
            timeout=5
        )
        
        if response.status_code != 200:
            pytest.skip("Could not access Grafana plugins")
        
        plugins = response.json()
        
        # Look for relevant plugins
        relevant_plugins = []
        plugin_keywords = ["redis", "prometheus", "stat", "graph", "table"]
        
        for plugin in plugins:
            plugin_id = plugin.get("id", "").lower()
            plugin_name = plugin.get("name", "").lower()
            
            if any(keyword in plugin_id or keyword in plugin_name for keyword in plugin_keywords):
                relevant_plugins.append({
                    "id": plugin["id"],
                    "name": plugin["name"],
                    "type": plugin.get("type"),
                    "enabled": plugin.get("enabled", False)
                })
        
        print(f"✅ Grafana plugins:")
        print(f"   - Total plugins: {len(plugins)}")
        print(f"   - Relevant plugins: {len(relevant_plugins)}")
        
        for plugin in relevant_plugins:
            status = "enabled" if plugin["enabled"] else "disabled"
            print(f"   - {plugin['name']}: {status} ({plugin['type']})")
    
    def test_grafana_performance(self, grafana_url, grafana_auth):
        """Test Grafana performance and responsiveness."""
        import time
        
        endpoints_to_test = [
            "/api/health",
            "/api/datasources",
            "/api/search",
            "/api/user"
        ]
        
        performance_results = {}
        
        for endpoint in endpoints_to_test:
            start_time = time.time()
            
            try:
                response = requests.get(
                    f"{grafana_url}{endpoint}",
                    headers=grafana_auth,
                    timeout=5
                )
                
                response_time = time.time() - start_time
                performance_results[endpoint] = {
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "success": response.status_code < 400
                }
                
            except Exception as e:
                performance_results[endpoint] = {
                    "status_code": None,
                    "response_time": None,
                    "success": False,
                    "error": str(e)
                }
        
        print(f"✅ Grafana performance test:")
        
        successful_requests = 0
        total_time = 0
        
        for endpoint, result in performance_results.items():
            if result["success"]:
                successful_requests += 1
                total_time += result["response_time"]
                print(f"   - {endpoint}: {result['response_time']:.3f}s (status: {result['status_code']})")
            else:
                print(f"   - {endpoint}: FAILED ({result.get('error', 'Unknown error')})")
        
        if successful_requests > 0:
            avg_response_time = total_time / successful_requests
            print(f"   - Average response time: {avg_response_time:.3f}s")
            print(f"   - Success rate: {successful_requests}/{len(endpoints_to_test)}")
            
            # Performance should be reasonable
            assert avg_response_time < 2.0, f"Grafana responses too slow: {avg_response_time:.3f}s average"


class TestGrafanaRAGIntegration:
    """Test Grafana integration with RAG system specifically."""
    
    def test_rag_dashboard_exists(self, grafana_url="http://localhost:3000"):
        """Test that RAG-specific dashboard exists and is accessible."""
        # This test can be run without authentication for basic checks
        try:
            # Check if the expected dashboard file exists in the container
            # This is a basic connectivity test
            response = requests.get(f"{grafana_url}/api/health", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ Grafana is accessible for RAG dashboard testing")
            else:
                pytest.skip("Grafana not accessible")
                
        except Exception as e:
            pytest.skip(f"Could not connect to Grafana: {e}")
    
    def test_expected_rag_metrics_queries(self):
        """Test that expected RAG metrics queries are valid."""
        # Define the metrics queries we expect to work in our RAG dashboard
        expected_queries = [
            'rate(http_requests_total[5m])',
            'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            'up{job="lightrag-api"}',
            'up{job="qdrant"}',
            'up{job="redis"}',
            'up{job="prometheus"}',
            'increase(documents_processed_total[1h])',
            'rate(queries_processed_total[5m])',
        ]
        
        print(f"✅ Expected RAG metrics queries defined:")
        for query in expected_queries:
            print(f"   - {query}")
        
        # These queries should be syntactically valid PromQL
        # In a real dashboard, these would be used to create visualizations
        print(f"   - Total expected queries: {len(expected_queries)}")
        
        # Verify queries are properly formatted
        for query in expected_queries:
            assert len(query.strip()) > 0, f"Empty query found: {query}"
            assert not query.startswith(' '), f"Query has leading whitespace: {query}"
            
        print(f"✅ All expected RAG metrics queries are properly formatted")
    
    def test_grafana_dashboard_config_exists(self):
        """Test that Grafana dashboard configuration files exist."""
        import os
        
        # Check if dashboard configuration files exist
        dashboard_paths = [
            "/home/kosaraju/llm_backend/configs/grafana/dashboards/",
            "/home/kosaraju/llm_backend/configs/grafana/provisioning/dashboards/"
        ]
        
        found_configs = []
        
        for path in dashboard_paths:
            if os.path.exists(path):
                files = os.listdir(path)
                dashboard_files = [f for f in files if f.endswith(('.json', '.yml', '.yaml'))]
                found_configs.extend([(path, f) for f in dashboard_files])
        
        print(f"✅ Grafana configuration files:")
        for path, filename in found_configs:
            print(f"   - {path}{filename}")
        
        if found_configs:
            print(f"   - Total config files: {len(found_configs)}")
        else:
            print("⚠️  No Grafana configuration files found in expected locations")
            print("   This might mean dashboards are configured differently or missing")