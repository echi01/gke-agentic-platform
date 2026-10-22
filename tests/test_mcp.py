import importlib.util, pathlib, unittest, json
p=pathlib.Path(__file__).resolve().parents[1]/"operations/mcp/server.py"
spec=importlib.util.spec_from_file_location("inspector",p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Fake:
 namespace="example-tenant"
 def __init__(self):self.calls=[]
 def query(self,path):
  self.calls.append(path)
  return {"items":[{"metadata":{"name":"example"},"spec":{"containers":[{"env":[{"value":"private-value"}]}]},"message":"private-message","status":{"phase":"Running"}}]}
class Tests(unittest.TestCase):
 def test_tools_do_not_expose_shell_secrets_or_arbitrary_paths(self):
  c=Fake()
  for params in [{"name":"exec"},{"name":"pods","arguments":{"namespace":"other"}},{"name":"pods","arguments":{"command":"delete"}}]:
   self.assertIn("error",m.reply({"id":1,"method":"tools/call","params":params},c))
  self.assertEqual(c.calls,[])
 def test_metadata_is_bounded_and_redacted(self):
  c=Fake();result=m.reply({"id":1,"method":"tools/call","params":{"name":"pods"}},c)
  self.assertNotIn("private-value",json.dumps(result));self.assertNotIn("private-message",json.dumps(result))
  self.assertEqual(c.calls,["/api/v1/namespaces/example-tenant/pods?limit=50"])
 def test_protocol_negotiation_and_notifications(self):
  c=Fake()
  self.assertIsNone(m.reply({"method":"notifications/initialized"},c))
  for version in m.PROTOCOLS:
   self.assertEqual(m.reply({"id":1,"method":"initialize","params":{"protocolVersion":version}},c)["result"]["protocolVersion"],version)
 def test_namespace_cannot_be_a_path(self):
  for value in ["../kube-system","a/b","", "UPPER"]:
   with self.assertRaises(ValueError):m.Client(value)
 def test_only_inspection_tools_are_advertised(self):
  result=m.reply({"id":1,"method":"tools/list"},Fake())
  self.assertEqual({t["name"] for t in result["result"]["tools"]},set(m.TOOLS))
  self.assertTrue(all(t["inputSchema"]["additionalProperties"] is False for t in result["result"]["tools"]))
if __name__=="__main__":unittest.main()
