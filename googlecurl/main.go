package main

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"os"
	"strings"

	"github.com/CUCyber/ja3transport"
	"github.com/alecthomas/kong"
)

// Captured from Wireshark when performing successful login via
// Raccoon desktop app and extracted from pcap using pyja3
//
// MD5 is dff8a0aa1c904aaea76c5bf624e88333
const googleJA3 = "769,4-5-47-53-49154-49156-49157-49164-49166-49167-49159-49161-49162-49169-49171-49172-51-57-50-56-10-49155-49165-49160-49170-22-19-9-21-18-3-8-20-17-255,11-10,14-13-25-11-12-24-9-10-22-23-8-6-7-20-21-4-5-18-19-1-2-3-15-16-17,0-1-2"

var args struct {
	URL     string   `arg:"" help:"Fully qualified URL to contact"`
	Method  string   `short:"X" name:"method" help:"HTTP method to use" default:"GET"`
	Headers []string `short:"H" name:"header" help:"Additional http headers in format 'Header: Value'"`
	Body    string   `name:"body" help:"Request body, must be UTF-8 due to limitation in argument parser"`
}

func mainE() error {
	kong.Parse(&args)
	parsedURL, err := url.Parse(args.URL)
	if err != nil {
		return err
	}
	parsedHeaders := http.Header{}
	for _, header := range args.Headers {
		splits := strings.SplitN(header, ": ", 2)
		if len(splits) != 2 {
			return fmt.Errorf("bad header format: %v", header)
		}
		key := splits[0]
		value := splits[1]
		parsedHeaders.Add(key, value)
	}
	if err != nil {
		return err
	}
	req := http.Request{
		Method: args.Method,
		URL:    parsedURL,
		Header: parsedHeaders,
		Body:   ioutil.NopCloser(bytes.NewReader([]byte(args.Body))),
	}
	client, err := ja3transport.NewWithString(googleJA3)
	if err != nil {
		return err
	}
	resp, err := client.Do(&req)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "status %s\n", resp.Status)
	for key, vals := range resp.Header {
		for _, val := range vals {
			fmt.Fprintf(os.Stderr, "header %s: %s\n", key, val)
		}
	}
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "body %d bytes\n", len(respBody))
	fmt.Printf("%s", respBody)
	return nil
}

func main() {
	err := mainE()
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %s\n", err.Error())
		os.Exit(1)
	}
}
