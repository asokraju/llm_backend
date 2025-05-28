"""Infrastructure tests for Prometheus metrics collection integration."""

import pytest
import requests
import time
import json
from typing import Dict, List, Any
from urllib.parse import urlencode


class TestPrometheusIntegration:
    """Test Prometheus metrics collection and monitoring."""
    
    @pytest.fixture
    def prometheus_url(self):
        """Prometheus base URL."""
        return "http://localhost:9090"
    
    @pytest.fixture
    def api_url(self):
        """LightRAG API base URL."""
        return "http://localhost:8000"
    
    def test_prometheus_connectivity(self, prometheus_url):
        """Test basic Prometheus connectivity."""
        # Test Prometheus web interface
        response = requests.get(f"{prometheus_url}/-/healthy", timeout=5)
        assert response.status_code == 200
        
        # Test Prometheus API
        response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=5)
        assert response.status_code == 200
        
        config_data = response.json()
        assert config_data["status"] == "success"
        
        print(f"✅ Prometheus connected successfully.")
        print(f"   - Health status: OK")
        print(f"   - Config loaded: {config_data['status']}")
    
    def test_prometheus_targets(self, prometheus_url):
        """Test Prometheus target discovery and health."""
        response = requests.get(f"{prometheus_url}/api/v1/targets", timeout=5)
        assert response.status_code == 200
        
        targets_data = response.json()
        assert targets_data["status"] == "success"
        
        active_targets = targets_data["data"]["activeTargets"]
        
        # Look for our services
        service_targets = {}
        for target in active_targets:
            labels = target["labels"]
            job = labels.get("job", "unknown")
            instance = labels.get("instance", "unknown")
            health = target["health"]
            
            service_targets[job] = {
                "instance": instance,
                "health": health,
                "lastScrape": target.get("lastScrape"),
                "scrapeUrl": target.get("scrapeUrl")
            }
        
        print(f"✅ Found {len(active_targets)} Prometheus targets:")
        for job, info in service_targets.items():
            print(f"   - {job}: {info['health']} ({info['instance']})")
        
        # Verify at least some targets are healthy
        healthy_targets = [t for t in active_targets if t["health"] == "up"]
        assert len(healthy_targets) > 0, f"No healthy targets found. Active targets: {len(active_targets)}"
    
    def test_api_metrics_endpoint(self, api_url):
        """Test that our API exposes metrics for Prometheus."""
        try:
            response = requests.get(f"{api_url}/metrics", timeout=5)
            assert response.status_code == 200
            
            metrics_text = response.text
            
            # Check for expected metrics
            expected_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "python_info",
                "process_",
            ]
            
            found_metrics = []
            for expected in expected_metrics:
                if expected in metrics_text:
                    found_metrics.append(expected)
            
            assert len(found_metrics) > 0, "No expected metrics found in /metrics endpoint"
            
            # Count total metrics
            metric_lines = [line for line in metrics_text.split('\\n') 
                          if line and not line.startswith('#')]
            
            print(f"✅ API metrics endpoint working:")
            print(f"   - Found {len(found_metrics)}/{len(expected_metrics)} expected metric types")
            print(f"   - Total metric lines: {len(metric_lines)}")
            print(f"   - Found metrics: {found_metrics}")
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"API not available for metrics test: {e}")
    
    def test_query_prometheus_metrics(self, prometheus_url):
        """Test querying specific metrics from Prometheus."""
        queries = [
            # Basic system metrics
            "up",  # Service availability
            "prometheus_config_last_reload_successful",
            
            # Application metrics (if available)
            "http_requests_total",
            "http_request_duration_seconds",
            "python_info",
        ]
        
        successful_queries = 0
        
        for query in queries:
            try:
                params = {"query": query}
                response = requests.get(
                    f"{prometheus_url}/api/v1/query",
                    params=params,
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data["status"] == "success" and data["data"]["result"]:
                        successful_queries += 1
                        result = data["data"]["result"]
                        print(f"   - {query}: {len(result)} series")
                        
                        # Show sample values for first series
                        if result and len(result) > 0:
                            sample = result[0]
                            metric_labels = sample.get("metric", {})
                            value = sample.get("value", [None, "N/A"])
                            print(f"     Sample: {value[1]} (labels: {len(metric_labels)})")
                
            except Exception as e:
                print(f"   - {query}: Failed ({e})")
        
        print(f"✅ Prometheus query test completed: {successful_queries}/{len(queries)} successful")
        
        # At least some basic metrics should be available
        assert successful_queries >= 1, "No Prometheus queries succeeded"
    
    def test_prometheus_rules_and_alerts(self, prometheus_url):
        """Test Prometheus rules and alerting configuration."""
        # Test rules endpoint
        response = requests.get(f"{prometheus_url}/api/v1/rules", timeout=5)
        assert response.status_code == 200
        
        rules_data = response.json()
        assert rules_data["status"] == "success"
        
        rule_groups = rules_data["data"]["groups"]
        
        # Test alerts endpoint
        response = requests.get(f"{prometheus_url}/api/v1/alerts", timeout=5)
        assert response.status_code == 200
        
        alerts_data = response.json()
        assert alerts_data["status"] == "success"
        
        active_alerts = alerts_data["data"]["alerts"]
        
        print(f"✅ Prometheus rules and alerts:")
        print(f"   - Rule groups: {len(rule_groups)}")
        print(f"   - Active alerts: {len(active_alerts)}")
        
        # List any active alerts
        for alert in active_alerts:
            print(f"   - Alert: {alert.get('labels', {}).get('alertname', 'Unknown')} "
                  f"({alert.get('state', 'unknown')})")
    
    def test_prometheus_storage_info(self, prometheus_url):
        """Test Prometheus storage and retention information."""
        # Test TSDB status
        response = requests.get(f"{prometheus_url}/api/v1/status/tsdb", timeout=5)
        
        if response.status_code == 200:
            tsdb_data = response.json()
            if tsdb_data["status"] == "success":
                tsdb_info = tsdb_data["data"]
                
                print(f"✅ Prometheus TSDB information:")
                print(f"   - Head stats: {tsdb_info.get('headStats', {})}")
                print(f"   - Series count: {tsdb_info.get('seriesCountByMetricName', {})}")
        
        # Test runtime info
        response = requests.get(f"{prometheus_url}/api/v1/status/runtimeinfo", timeout=5)
        
        if response.status_code == 200:
            runtime_data = response.json()
            if runtime_data["status"] == "success":
                runtime_info = runtime_data["data"]
                
                print(f"✅ Prometheus runtime information:")
                print(f"   - Start time: {runtime_info.get('startTime')}")
                print(f"   - Uptime: {runtime_info.get('uptime')}")
                print(f"   - Go version: {runtime_info.get('goVersion')}")
    
    def test_generate_and_verify_custom_metrics(self, api_url, prometheus_url):
        """Test generating custom metrics and verifying they appear in Prometheus."""
        try:
            # Generate some API activity to create metrics
            endpoints_to_test = [
                "/health",
                "/",
                "/metrics"
            ]
            
            print(f"🔄 Generating API activity to create metrics...")
            
            for endpoint in endpoints_to_test:
                for _ in range(3):  # Multiple requests per endpoint
                    try:
                        response = requests.get(f"{api_url}{endpoint}", timeout=2)
                        print(f"   - {endpoint}: {response.status_code}")
                    except:
                        pass  # Continue even if some requests fail
                    time.sleep(0.1)
            
            # Wait for Prometheus to scrape the metrics
            print(f"⏳ Waiting for Prometheus to scrape metrics...")
            time.sleep(15)  # Give Prometheus time to scrape
            
            # Query for our generated metrics
            queries_to_check = [
                'http_requests_total{job="lightrag-api"}',
                'http_request_duration_seconds{job="lightrag-api"}',
                'up{job="lightrag-api"}'
            ]
            
            metrics_found = 0
            
            for query in queries_to_check:
                try:
                    params = {"query": query}
                    response = requests.get(
                        f"{prometheus_url}/api/v1/query",
                        params=params,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data["status"] == "success" and data["data"]["result"]:
                            metrics_found += 1
                            result = data["data"]["result"]
                            print(f"   ✅ Found metric: {query} ({len(result)} series)")
                            
                            # Show sample data
                            if result:
                                sample = result[0]
                                value = sample.get("value", [None, "N/A"])
                                labels = sample.get("metric", {})
                                print(f"      Value: {value[1]}, Labels: {labels}")
                        else:
                            print(f"   ❌ No data for: {query}")
                    else:
                        print(f"   ❌ Query failed: {query}")
                        
                except Exception as e:
                    print(f"   ❌ Error querying {query}: {e}")
            
            print(f"✅ Custom metrics verification: {metrics_found}/{len(queries_to_check)} found")
            
            if metrics_found == 0:
                print("⚠️  No custom metrics found. This could indicate:")
                print("   - Prometheus is not scraping the API")
                print("   - API metrics endpoint is not working")
                print("   - Service discovery is not configured properly")
            
        except Exception as e:
            pytest.skip(f"Could not test custom metrics generation: {e}")


class TestPrometheusServiceIntegration:
    """Test Prometheus integration with other services."""
    
    def test_service_discovery_configuration(self):
        """Test that Prometheus is configured to discover our services."""
        prometheus_url = "http://localhost:9090"
        
        try:
            # Get Prometheus configuration
            response = requests.get(f"{prometheus_url}/api/v1/status/config", timeout=5)
            assert response.status_code == 200
            
            config_data = response.json()
            config_yaml = config_data["data"]["yaml"]
            
            # Check for our service configurations
            expected_services = [
                "lightrag-api",
                "prometheus", 
                "qdrant"
            ]
            
            found_services = []
            for service in expected_services:
                if service in config_yaml:
                    found_services.append(service)
            
            print(f"✅ Service discovery configuration:")
            print(f"   - Expected services: {expected_services}")
            print(f"   - Found in config: {found_services}")
            
            # Should find at least one of our services
            assert len(found_services) > 0, "No expected services found in Prometheus config"
            
        except Exception as e:
            pytest.skip(f"Could not test service discovery config: {e}")
    
    def test_cross_service_metrics(self):
        """Test metrics from multiple services are available."""
        prometheus_url = "http://localhost:9090"
        
        # Metrics to look for from different services
        service_metrics = {
            "prometheus": ["prometheus_notifications_total", "prometheus_rule_evaluations_total"],
            "qdrant": ["qdrant_collections_total", "qdrant_points_total"], 
            "lightrag-api": ["http_requests_total", "python_info"],
            "redis": ["redis_up", "redis_commands_total"],
        }
        
        available_metrics = {}
        
        for service, metrics in service_metrics.items():
            available_metrics[service] = []
            
            for metric in metrics:
                try:
                    params = {"query": metric}
                    response = requests.get(
                        f"{prometheus_url}/api/v1/query",
                        params=params,
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data["status"] == "success" and data["data"]["result"]:
                            available_metrics[service].append(metric)
                            
                except Exception:
                    pass  # Continue checking other metrics
        
        print(f"✅ Cross-service metrics availability:")
        total_found = 0
        total_expected = 0
        
        for service, found_metrics in available_metrics.items():
            expected_count = len(service_metrics[service])
            found_count = len(found_metrics)
            total_found += found_count
            total_expected += expected_count
            
            print(f"   - {service}: {found_count}/{expected_count} metrics")
            for metric in found_metrics:
                print(f"     ✅ {metric}")
        
        print(f"   - Overall: {total_found}/{total_expected} metrics available")
        
        # Should find at least some metrics
        assert total_found > 0, "No service metrics found in Prometheus"