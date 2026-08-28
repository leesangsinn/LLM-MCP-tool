require 'sketchup.rb'
require 'socket'
require 'thread'

module MCPServer
  @queue ||= Queue.new
  @server ||= nil
  @server_thread ||= nil
  @timer_id ||= nil

  def self.start
    stop()

    # Retry loop to wait for Windows to fully release the port
    retries = 0
    begin
      @server = TCPServer.new('127.0.0.1', 8080)
    rescue Errno::EADDRINUSE, Errno::EACCES => e
      retries += 1
      if retries <= 10
        sleep 0.5
        retry
      else
        puts "Failed to open port 8080 after multiple attempts: #{e.message}"
        return
      end
    end
    
    puts "MCP Server is listening on 127.0.0.1:8080"

    @server_thread = Thread.new do
      loop do
        begin
          client = @server.accept
          script = client.read # Reads until EOF
          @queue << { client: client, script: script }
        rescue => e
          puts "MCP Server Thread Error: #{e.message}"
          break if @server.closed?
        end
      end
    end

    # Poll queue from main thread
    @timer_id = UI.start_timer(0.1, true) do
      while !@queue.empty?
        job = @queue.pop(true) rescue nil
        if job
          client = job[:client]
          script = job[:script]
          begin
            # Execute on main thread
            result = eval(script, TOPLEVEL_BINDING)
            client.puts(result.to_s) rescue nil
          rescue Exception => e
            client.puts("Error: #{e.message}\n#{e.backtrace.join("\n")}") rescue nil
          ensure
            client.close rescue nil
          end
        end
      end
    end
  end

  def self.stop
    if @timer_id
      UI.stop_timer(@timer_id) rescue nil
      @timer_id = nil
    end
    if @server
      @server.close rescue nil
      @server = nil
    end
    if @server_thread
      @server_thread.kill rescue nil
      @server_thread = nil
    end
    puts "MCP Server stopped."
  end
end

unless file_loaded?(__FILE__)
  # Defer start to ensure SketchUp's event loop is fully initialized
  UI.start_timer(5.0, false) do
    MCPServer.start
  end
  file_loaded(__FILE__)
end
