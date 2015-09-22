from midiUtils import *

__author__ = "Stephan Pieterse"

# TODO i would still like to add velocity based actions.... but it is starting to look like hell on earth from here...
# TODO do we need rest actions?


class BlenderObj:
    useAutoGeneratedNames = False
    autoGenerateString = ""
    outputScript = ""
    lastCommand = ""
    blenderObject = ""
    framerate = 25
    configfile = None
    midiResolution = 480
    BPM = 120
    currentNewAction = ""
    guyConf = ""
    consolidatedAction = False
    hasAction = False
    overrideNoteLengths = False
    newNoteLength = 0

    def __init__(self, blenderObject, conffile, midires, BPM):
        self.assignObject(blenderObject)
        self.setConfigfile(conffile)
        confOptions = self.configfile.getConfig("options")
        self.useAutoGeneratedNames = confOptions["useAutoGeneratedNames"]
        if self.useAutoGeneratedNames:
            self.autoGenerateString = confOptions["autoActionNameFormat"]
        self.midiResolution = midires
        self.BPM = BPM
        tempConf = self.configfile.getConfig("blenderobjects")
        self.guyConf = tempConf[blenderObject]

        try:
            self.newNoteLength = self.guyConf["soundOptions"]["overrideNoteLength"]
            self.newNoteLength = self.millisecondsToFrames(self.newNoteLength)
            self.overrideNoteLengths = True
        except KeyError:
            self.overrideNoteLengths = False

        try:
            self.consolidatedAction = self.guyConf["objectOptions"]["createNewAction"]
            if self.consolidatedAction:
                self.currentNewAction = "consolidatedAction"
                self.outputScript = ""
                self.outputScript += "newact = bpy.data.actions.new(\"{}\") \n".format(self.currentNewAction)
                self.outputScript += "newobj = {} \n".format(self.get_data_set())
                self.outputScript += "newobj.animation_data_create() \n"
                self.outputScript += "newobj.animation_data.action = newact \n"
        except KeyError:
            self.consolidatedAction = False

    def parse_auto_action(self, autoString, objName, actType, notePitch, noteVel):
        autoString.replace("$objectname$", objName)
        autoString.replace("$actiontype$", actType)
        autoString.replace("$note$", notePitch)
        autoString.replace("$velocity$", noteVel)
        return autoString

    def set_framerate(self, fps):
        self.framerate = fps

    def setConfigfile(self, conffile):
        self.configfile = conffile

    def assignObject(self, objectName):
        self.blenderObject = objectName

    def insert_note(self, channel, pitch, velocity, sframe, eframe):
        self.hasAction = True

        if self.overrideNoteLengths:
            eframe = sframe + self.newNoteLength;

        if self.consolidatedAction == False:
            self.update_action("insert", [channel, pitch, velocity, sframe, eframe])
        else:
            self.continue_action("insert", [channel, pitch, velocity, sframe, eframe])

    def millisecondsToFrames(self, milliseconds):
        fps = self.framerate # 25
        inSeconds = milliseconds / 1000.0 # 250 / 1000.0 = 0.25
        frames = fps * inSeconds # 25 * .025 = 6.25

        return frames

    def pitch_as_note(self, pitch):
        notes = ['a', 'as', 'b', 'c', 'cs', 'd', 'ds', 'e', 'f', 'fs', 'g', 'gs']
        pitch_octave = (pitch / 12) - 1
        pitch_note = pitch % 12
        pitch_as_note = notes[pitch_note] + str(pitch_octave)
        return pitch_as_note

    def setNLABlends(self):
        # modify action attributes
        modexec = "nla_extrap = '{}'".format(self.guyConf["objectOptions"]["defaultNLAHold"])
        modexec += "\n"
        modexec += "nla_blend = '{}'".format(self.guyConf["objectOptions"]["defaultNLABlend"])
        modexec += "\n"
        modexec += "nla_autoblend = {}".format(self.guyConf["objectOptions"]["defaultNLAAutoBlend"])
        modexec += "\n"
        return modexec

    def get_data_set(self):
        actionobj = ""
        guyAnimType = self.guyConf["objectOptions"]["objectType"]
        selObjName = self.guyConf["name"]

        if guyAnimType == "object":
            actionobj = "bpy.data.objects[\"{}\"]".format(selObjName)

        if guyAnimType == "material":
            actionobj = "bpy.data.materials[\"{}\"]".format(selObjName)

        if guyAnimType == "shapekey":
            actionobj = "bpy.data.shape_keys[\"{}\"]".format(selObjName)

        if actionobj == "":
            print "invalid object type assignment"
            exit(1)

        return actionobj

    def getPitchAction(self,pitch):
        noPitchAction = False
        pitchAction = None
        pitchAsNote = self.pitch_as_note(pitch)
        # print(pitchAsNote) # for debuggings

        # if this is true, we can just parse and return
        if self.useAutoGeneratedNames:
            auto_string = self.autoGenerateString
            objName = self.guyConf["name"]
            pitchAction = self.parse_auto_action(auto_string,objName,"NOTE",pitchAsNote,0)
            preNoteAction = self.parse_auto_action(auto_string,objName,"PRENOTE",pitchAsNote,0)
            attackAction = self.parse_auto_action(auto_string,objName,"ATTACK",pitchAsNote,0)
            releaseAction = self.parse_auto_action(auto_string,objName,"RELEASE",pitchAsNote,0)
            vibratoAction = self.parse_auto_action(auto_string,objName,"VIBRATO",pitchAsNote,0)
            waitAction = self.parse_auto_action(self.autoGenerateString,self.blenderObject,"WAIT",pitchAsNote,0)
            attackTime = self.guyConf["soundOptions"]["attack"]
            attackTime = self.millisecondsToFrames(attackTime)
            releaseTime = self.guyConf["soundOptions"]["release"]
            releaseTime = self.millisecondsToFrames(releaseTime)
            vibratoTime = self.guyConf["soundOptions"]["vibratoDelay"]
            vibratoTime = self.millisecondsToFrames(vibratoTime)
        else:
            try:
                pitchAction = self.guyConf["notes"][str(pitchAsNote)]["noteAction"]
            except KeyError:
                if self.guyConf["objectOptions"]["noDefaultAction"] == False:
                    pitchAction = self.guyConf["notes"]["default"]["noteAction"]
                else:
                    noPitchAction = True

            try:
                preNoteAction = self.guyConf["notes"][str(pitchAsNote)]["preNoteAction"]
            except KeyError:
                preNoteAction = ""

            try:
                attackAction = self.guyConf["notes"][str(pitchAsNote)]["attackAction"]
                attackTime = self.guyConf["soundOptions"]["attack"]
                attackTime = self.millisecondsToFrames(attackTime)
            except KeyError:
                attackAction = ""
                attackTime = self.millisecondsToFrames(0)

            try:
                releaseAction = self.guyConf["notes"][str(pitchAsNote)]["releaseAction"]
                releaseTime = self.guyConf["soundOptions"]["release"]
                releaseTime = self.millisecondsToFrames(releaseTime)
            except KeyError:
                releaseAction = ""
                releaseTime = self.millisecondsToFrames(0)

            try:
                vibratoAction = self.guyConf["notes"][str(pitchAsNote)]["vibratoAction"]
                vibratoTime = self.guyConf["soundOptions"]["vibratoDelay"]
                vibratoTime = self.millisecondsToFrames(vibratoTime)
            except KeyError:
                vibratoAction = ""
                vibratoTime = self.millisecondsToFrames(0)

        retVal = {'pitch':pitchAction, 'noPitch': noPitchAction, 'preNote':preNoteAction,
                  'attack':attackAction, 'attackTime':attackTime,
                  'release':releaseAction, 'releaseTime':releaseTime,
                  'vibrato':vibratoAction, 'vibratoTime': vibratoTime}

        return retVal

    def update_action_delay(self,at_frame):
        midiUtil = midiUtility(self.midiResolution, self.BPM, self.framerate)

        try:
            obj_delay = self.guyConf["objectOptions"]["objectDelay"]
            at_frame += midiUtil.tickToFrame(obj_delay)
        except KeyError:
            # obj_delay = 0
            pass

        return at_frame

    def generateScript(self, pitch, vel, sframe, eframe):
        restAction = self.guyConf["restAction"]
        selObjName = self.guyConf["name"]
        should_create = self.guyConf["objectOptions"]["shouldCreate"]
        destroy_when_done = self.guyConf["objectOptions"]["destroyWhenDone"]

        if destroy_when_done and not should_create:
            print("you will be destroying {} multiple times... script will run but check your config.".format(selObjName))

        standard_data = ""

        pitch_result = self.getPitchAction(pitch)
        pitchAction = pitch_result['pitch']
        no_pitch_action = pitch_result['noPitch']
        preNoteAction = pitch_result['preNote']
        attackAction = pitch_result['attack']
        attackTime = pitch_result['attackTime']
        releaseAction = pitch_result['release']
        releaseTime = pitch_result['releaseTime']
        vibratoAction = pitch_result['vibrato']
        vibratoTime = pitch_result['vibratoTime']
        waitAction = pitch_result['wait']
        sframe = self.update_action_delay(sframe)
        eframe = self.update_action_delay(eframe)

        if no_pitch_action is False:
            actionobj = self.get_data_set()
            cmd_nla_blends = self.setNLABlends()

            with open("blenderfunc/blender_standardActionScript.py",'r') as f:
                standard_data = f.read()
                standard_data = standard_data.replace("%PITCH_ACTION%",pitchAction)
                standard_data = standard_data.replace("%PRENOTE_ACTION%", preNoteAction)
                standard_data = standard_data.replace("%ATTACK_ACTION%", attackAction)
                standard_data = standard_data.replace("%ATTACK_TIME%", str(attackTime))
                standard_data = standard_data.replace("%RELEASE_ACTION%", releaseAction)
                standard_data = standard_data.replace("%RELEASE_TIME%", str(releaseTime))
                standard_data = standard_data.replace("%VIBRATO_ACTION%", vibratoAction)
                standard_data = standard_data.replace("%VIBRATO_TIME%", str(vibratoTime))
                standard_data = standard_data.replace("%REST_ACTION%", restAction)
                standard_data = standard_data.replace("%CALCULATED_FRAME%",str(sframe))
                # standard_data = standard_data.replace("%SEL_OBJECT_NAME%",selObjName)
                if should_create is True:
                    dupl_command = "actionObj = duplicateObject({}, '{}', '{}')".format('bpy.context.scene',selObjName + "_copy",selObjName)
                    dupl_command += "\n"
                    dupl_command += "actionObj = {}".format("bpy.data.objects[actionObj]")
                    dupl_command += "\n"
                    dupl_command += "actionObj.animation_data_create()"
                else:
                    dupl_command = "actionObj = {}".format(actionobj)
                standard_data = standard_data.replace("%DUPLICATE_ME_SECTION%",dupl_command)
                standard_data = standard_data.replace("%ACTION_OBJ%",actionobj)
                standard_data = standard_data.replace("%NLA_BLENDS%",cmd_nla_blends)
                standard_data = standard_data.replace("%NOTE_START_FRAME%", str(sframe))
                standard_data = standard_data.replace("%NOTE_END_FRAME%", str(eframe))
                if destroy_when_done is True:
                    kf = open("blenderfunc/blender_dupliKillScript.py")
                    killCommand = kf.read()
                    kf.close
                    killCommand = killCommand . replace("%ACTION_OBJ%",'actionObj')
                else:
                    killCommand = ""
                standard_data = standard_data.replace("%DUPLI_KILL%", killCommand)
                f.close()

        return standard_data

    def continueScript(self, pitch, vel, sframe, eframe):
        should_create = self.guyConf["objectOptions"]["shouldCreate"]
        destroy_when_done = self.guyConf["objectOptions"]["destroyWhenDone"]
        pitch_result = self.getPitchAction(pitch)
        pitchAction = pitch_result['pitch']
        no_pitch_action = pitch_result['noPitch']
        preNoteAction = pitch_result['preNote']
        attackAction = pitch_result['attack']
        attackTime = pitch_result['attackTime']
        releaseAction = pitch_result['release']
        releaseTime = pitch_result['releaseTime']
        vibratoAction = pitch_result['vibrato']
        vibratoTime = pitch_result['vibratoTime']
        script = ""
        restAction = self.guyConf["restAction"]
        selObjName = self.guyConf["name"]

        sframe = self.update_action_delay(sframe)
        eframe = self.update_action_delay(eframe)

        if no_pitch_action is False:
            # actionobj = self.get_data_set()

            with open("blenderfunc/blender_continueActionScript.py", 'r') as f:
                script = f.read()
                script = script.replace("%CURRENT_ACTION%", pitchAction)
                script = script.replace("%PRENOTE_ACTION%", preNoteAction)
                script = script.replace("%ATTACK_ACTION%", attackAction)
                script = script.replace("%ATTACK_TIME%", str(attackTime))
                script = script.replace("%RELEASE_ACTION%", releaseAction)
                script = script.replace("%RELEASE_TIME%", str(releaseTime))
                script = script.replace("%VIBRATO_ACTION%", vibratoAction)
                script = script.replace("%VIBRATO_TIME%", str(vibratoTime))
                script = script.replace("%REST_ACTION%", restAction)
                script = script.replace("%NEW_ACTION%", self.currentNewAction)
                script = script.replace("%CALCULATED_FRAME%", str(sframe))
                # script = script.replace("%CURRENT_OBJECT%", self.guyConf["name"])
                if should_create is True:
                    dupl_command = "actionObj = duplicateObject({}, '{}', '{}')".format('bpy.context.scene', selObjName + "_copy", selObjName)
                    dupl_command += "\n"
                    dupl_command += "actionObj = {}".format("bpy.data.objects[actionObj]")
                    dupl_command += "\n"
                    dupl_command += "actionObj.animation_data_create()"
                else:
                    dupl_command = "actionObj = {}".format(selObjName)
                script = script.replace("%DUPLICATE_ME_SECTION%",dupl_command)
                script = script.replace("%NOTE_START_FRAME%", str(sframe))
                script = script.replace("%NOTE_END_FRAME%", str(eframe))

                f.close()

        return script

    def continue_action(self, commandName, command):
        if commandName == "insert":
            pitch = command[1]
            vel = command[2]
            sframe = command[3]
            eframe = command[4]

        new_command = self.continueScript(pitch, vel, sframe, eframe)
        self.outputScript += new_command

    def update_action(self, commandName, command):
        if commandName == "insert":
            pitch = command[1]
            vel = command[2]
            sframe = command[3]
            eframe = command[4]

        new_command = self.generateScript(pitch, vel, sframe, eframe)
        self.outputScript += new_command

    def write_blender_script(self):
        out_config = self.configfile.getConfig("scriptOutput")
        output_script_name = out_config["name"]

        # print self.outputScript
        print "writing current actions to a file ..."

        if self.outputScript != "" and self.hasAction == True:
            with open(output_script_name, 'a') as f:
                f.write(self.outputScript)
                f.close
        print "done with {} ! processing next ...".format(self.blenderObject)
