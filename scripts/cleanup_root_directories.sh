#!/bin/bash
# Script to clean up root directories and ensure organized structure

echo "🧹 LightRAG Root Directory Cleanup"
echo "=================================="

# Check if Docker is running
if docker ps > /dev/null 2>&1; then
    echo "⚠️  Docker is running. Please stop services first:"
    echo "   docker-compose down"
    exit 1
fi

echo "✅ Docker is stopped. Proceeding with cleanup..."

# Function to safely move or remove directories
cleanup_directory() {
    local dir_name=$1
    local target_location=$2
    
    if [ -d "$dir_name" ]; then
        local size=$(du -sh "$dir_name" | cut -f1)
        echo
        echo "📁 Found: $dir_name ($size)"
        
        if [ -d "$target_location" ]; then
            echo "   Target already exists: $target_location"
            echo "   Comparing sizes..."
            local target_size=$(du -sh "$target_location" | cut -f1)
            echo "   Root: $size vs Organized: $target_size"
            
            # If root directory is significantly larger, back up organized and use root
            if [ "$size" != "$target_size" ]; then
                echo "   ⚠️  Sizes differ - manual review recommended"
                echo "   Renaming root directory to ${dir_name}_old for manual review"
                mv "$dir_name" "${dir_name}_old"
            else
                echo "   ✅ Sizes match - removing root directory"
                rm -rf "$dir_name"
            fi
        else
            echo "   Moving to organized location: $target_location"
            mkdir -p "$(dirname "$target_location")"
            mv "$dir_name" "$target_location"
        fi
    else
        echo "✅ $dir_name not found in root (already clean)"
    fi
}

# Clean up directories
cleanup_directory "test_basic_rag" "generated_data/test_basic_rag"
cleanup_directory "vllm_cache" "models/vllm_cache" 
cleanup_directory "rag_data" "generated_data/rag_data"
cleanup_directory "redis_data" "storage/redis_data"

# Handle permission issues for Docker-created directories
echo
echo "🔧 Handling Docker permission issues..."

for dir in vllm_cache redis_data; do
    if [ -d "$dir" ]; then
        echo "   Found Docker-owned directory: $dir"
        echo "   Adding to .gitignore and renaming for manual cleanup"
        mv "$dir" "${dir}_docker_old" 2>/dev/null || {
            echo "   Permission denied - will be cleaned up by Docker restart"
        }
    fi
done

echo
echo "📝 Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Legacy root directories (to be removed)
/test_basic_rag_old/
/vllm_cache_old/
/vllm_cache_docker_old/
/rag_data_old/
/redis_data_old/
/redis_data_docker_old/
EOF

echo
echo "✅ Cleanup complete!"
echo
echo "📋 Summary:"
echo "   - Docker Compose already uses organized paths"
echo "   - Root directories cleaned up or renamed for review"
echo "   - Any remaining Docker-owned directories will be recreated"
echo
echo "🚀 Next steps:"
echo "   1. Review any *_old directories and remove when satisfied"
echo "   2. Start services: docker-compose up -d"
echo "   3. Services will use the organized directory structure"

# Show final structure
echo
echo "📁 Final organized structure:"
echo "   generated_data/:"
ls -la generated_data/ 2>/dev/null | head -10
echo "   models/:"
ls -la models/ 2>/dev/null | head -5
echo "   storage/:"
ls -la storage/ 2>/dev/null | head -5